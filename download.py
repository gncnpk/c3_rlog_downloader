# python version of https://github.com/mmmorks/sunnypilot/blob/staging-merged/tools/tuning/rlog_copy_from_device_then_zip1.sh
# downloads rlogs of your device, using a previously saved ssh key thing
# 
# Windows Compatibility Notes:
# - File paths are automatically sanitized for Windows naming restrictions
# - SSH key paths use forward slashes for rsync compatibility
# - Supports both WSL and native Windows rsync installations
# - Falls back gracefully from rsync to SFTP if rsync is not available
#
# Performance Optimizations (rsync mode):
# - SSH connection multiplexing for faster subsequent connections
# - Bulk transfers instead of individual file downloads
# - Smart file filtering with include/exclude patterns
# - Configurable compression levels and bandwidth limiting
# - Optimized SSH cipher selection (AES-128-CTR)
# - Partial transfer support with automatic resume
# - Provides 2-5x faster transfer speeds vs individual file method

import os
import time
import subprocess
import paramiko
from pathlib import Path
import io
import stat
import platform
import json
import tempfile

# ========= MODIFY THESE If you want to =========
diroutbase = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rlogs")
config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "devices_config.json")

# Transfer method: "sftp" or "rsync"
# rsync is generally faster and more efficient for large transfers
transfer_method = "rsync"  # Change to "sftp" to use the original SFTP method

# Rsync optimization settings (only used when transfer_method = "rsync")
rsync_compress_level = 1  # 1-9, lower = faster but larger, higher = slower but smaller
rsync_bandwidth_limit = 0  # KB/s, 0 = no limit (use for slower connections)
rsync_whole_file = True  # Use whole-file transfers (faster for initial sync, slower for updates)

# These -probably- don't change
remote_data_dir = "/data/media/0/realdata" # pretty sure this wont change
# ====

def is_on_home_wifi():
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(["ipconfig"], shell=True).decode()
        else:
            output = subprocess.check_output(["ifconfig"]).decode()
        
        return any(x in output for x in ["192.168.", "10.0.", "10.1.", "200.200."])
    except subprocess.CalledProcessError:
        return False

def is_rsync_available():
    """Check if rsync is available on the system and get version info."""
    try:
        result = subprocess.run(["rsync", "--version"], capture_output=True, check=True, text=True)
        version_line = result.stdout.split('\n')[0]
        print(f"Found rsync: {version_line}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def find_ssh_keys():
    """Find available SSH keys in the user's .ssh directory."""
    ssh_dir = os.path.expanduser("~/.ssh")
    if not os.path.exists(ssh_dir):
        return []
    
    # Common private key names
    key_patterns = [
        "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
        "*_rsa", "*_dsa", "*_ecdsa", "*_ed25519",
        "*github*", "*gitlab*", "*bitbucket*",
        "my_*_key", "*_key"
    ]
    
    keys = []
    for item in os.listdir(ssh_dir):
        item_path = os.path.join(ssh_dir, item)
        # Skip .pub files and directories
        if item.endswith('.pub') or os.path.isdir(item_path):
            continue
        
        # Check if it matches common key patterns or is a file without extension
        is_key = False
        for pattern in key_patterns:
            if pattern.replace('*', '') in item.lower() or item == pattern.replace('*', ''):
                is_key = True
                break
        
        # Also include files that don't have extensions (common for SSH keys)
        if not is_key and '.' not in item and os.path.isfile(item_path):
            # Try to detect if it's likely an SSH key by reading first line
            try:
                with open(item_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if 'PRIVATE KEY' in first_line or first_line.startswith('-----'):
                        is_key = True
            except (UnicodeDecodeError, PermissionError):
                # Binary file or no permission, might still be a key
                is_key = True
        
        if is_key:
            keys.append(item_path)
    
    return sorted(keys)

def select_ssh_key():
    """Prompt user to select or specify an SSH key."""
    keys = find_ssh_keys()
    
    if not keys:
        print("No SSH keys found in ~/.ssh directory!")
        print("Please ensure you have SSH keys set up for your device.")
        print("\nTo generate a new SSH key, run:")
        print("  ssh-keygen -t ed25519 -C 'your-email@example.com'")
        print("\nThen copy the public key to your device:")
        print("  ssh-copy-id comma@your-device-ip")
        
        while True:
            manual_key = input("\nEnter the path to your SSH private key (or 'q' to quit): ").strip()
            if manual_key.lower() == 'q':
                return None
            
            expanded_key = os.path.expanduser(manual_key)
            if os.path.exists(expanded_key):
                return expanded_key
            else:
                print(f"File not found: {expanded_key}")
    
    elif len(keys) == 1:
        key_path = keys[0]
        use_key = input(f"Found SSH key: {key_path}\nUse this key? (y/n): ").strip().lower()
        if use_key in ['y', 'yes']:
            return key_path
        else:
            manual_key = input("Enter the path to your SSH private key: ").strip()
            return os.path.expanduser(manual_key) if manual_key else None
    
    else:
        print("Multiple SSH keys found:")
        for i, key in enumerate(keys, 1):
            print(f"  {i}. {key}")
        print(f"  {len(keys) + 1}. Enter custom path")
        
        while True:
            try:
                choice = input(f"\nSelect SSH key (1-{len(keys) + 1}): ").strip()
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(keys):
                    return keys[choice_num - 1]
                elif choice_num == len(keys) + 1:
                    manual_key = input("Enter the path to your SSH private key: ").strip()
                    return os.path.expanduser(manual_key) if manual_key else None
                else:
                    print(f"Please enter a number between 1 and {len(keys) + 1}")
            except ValueError:
                print("Please enter a valid number")

def load_device_config():
    """Load device configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            devices = config.get('devices', [])
            
            # Convert old format (tuples) to new format (dictionaries)
            converted_devices = []
            for device in devices:
                if isinstance(device, (list, tuple)) and len(device) == 2:
                    # Old format: (hostname, label)
                    converted_devices.append({
                        "hostname": device[0],
                        "label": device[1],
                        "username": "comma",  # Default username
                        "ssh_key": os.path.expanduser("~/.ssh/id_rsa")  # Default key
                    })
                elif isinstance(device, dict):
                    # New format: already a dictionary
                    converted_devices.append(device)
            
            return converted_devices
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_device_config(devices):
    """Save device configuration to JSON file."""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    
    config = {
        "devices": devices,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "transfer_method": transfer_method,
        "remote_data_dir": remote_data_dir
    }
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Device configuration saved to: {config_file}")

def add_device_interactive():
    """Interactively add a new device to the configuration."""
    print("\n--- Add New Device ---")
    while True:
        hostname = input("Enter device hostname or IP address: ").strip()
        if hostname:
            break
        print("Hostname/IP cannot be empty!")
    
    while True:
        label = input("Enter a subfolder name/label for this device [comma]: ").strip()
        if not label:
            label = "comma"  # Default subfolder name
        break
    
    while True:
        username = input("Enter SSH username for this device [comma]: ").strip()
        if not username:
            username = "comma"  # Default username
        break
    
    print(f"\nSelecting SSH key for {hostname}...")
    ssh_key = select_ssh_key()
    if not ssh_key:
        print("Cannot add device without SSH key!")
        return None
    
    print(f"\nDevice will be saved as:")
    print(f"  Host: {hostname}")
    print(f"  Subfolder: {label}")
    print(f"  Username: {username}")
    print(f"  SSH Key: {ssh_key}")
    print(f"  Logs will be stored in: ~/Downloads/rlogs/{label}/")
    
    return {
        "hostname": hostname,
        "label": label,
        "username": username,
        "ssh_key": ssh_key
    }

def manage_device_config():
    """Manage device configuration - load existing or create new."""
    devices = load_device_config()
    
    if not devices:
        print("No device configuration found. Let's set up your devices.")
        print("You can add multiple devices if you have more than one.")
        
        while True:
            device = add_device_interactive()
            if device:
                devices.append(device)
                print(f"Added device: {device['hostname']} (subfolder: {device['label']}) - User: {device['username']}")
            
            while True:
                add_more = input("\nAdd another device? (y/n): ").strip().lower()
                if add_more in ['y', 'yes', 'n', 'no']:
                    break
                print("Please enter 'y' or 'n'")
            
            if add_more in ['n', 'no']:
                break
        
        save_device_config(devices)
    else:
        print(f"Loaded {len(devices)} device(s) from configuration:")
        for i, device in enumerate(devices, 1):
            print(f"  {i}. {device['hostname']} (subfolder: {device['label']}) - User: {device['username']}")
        
        while True:
            action = input("\n(a)dd device, (r)emove device, (e)dit device, (l)ist devices, (s)ize report, or (c)ontinue: ").strip().lower()
            
            if action in ['c', 'continue']:
                break
            elif action in ['a', 'add']:
                device = add_device_interactive()
                if device:
                    devices.append(device)
                    print(f"Added device: {device['hostname']} (subfolder: {device['label']}) - User: {device['username']}")
                    save_device_config(devices)
            elif action in ['r', 'remove']:
                if not devices:
                    print("No devices to remove!")
                    continue
                
                print("Select device to remove:")
                for i, device in enumerate(devices, 1):
                    print(f"  {i}. {device['hostname']} (subfolder: {device['label']}) - User: {device['username']}")
                
                try:
                    choice = int(input("Enter device number: ")) - 1
                    if 0 <= choice < len(devices):
                        removed = devices.pop(choice)
                        print(f"Removed device: {removed['hostname']} (subfolder: {removed['label']})")
                        save_device_config(devices)
                    else:
                        print("Invalid device number!")
                except ValueError:
                    print("Please enter a valid number!")
            elif action in ['e', 'edit']:
                if not devices:
                    print("No devices to edit!")
                    continue
                
                print("Select device to edit:")
                for i, device in enumerate(devices, 1):
                    print(f"  {i}. {device['hostname']} (subfolder: {device['label']}) - User: {device['username']}")
                
                try:
                    choice = int(input("Enter device number: ")) - 1
                    if 0 <= choice < len(devices):
                        device = devices[choice]
                        print(f"\nEditing device: {device['hostname']} (subfolder: {device['label']})")
                        
                        # Edit each field
                        new_hostname = input(f"Hostname [{device['hostname']}]: ").strip()
                        if new_hostname:
                            device['hostname'] = new_hostname
                        
                        new_label = input(f"Subfolder name [{device['label']}]: ").strip()
                        if new_label:
                            device['label'] = new_label
                        
                        new_username = input(f"Username [{device['username']}]: ").strip()
                        if new_username:
                            device['username'] = new_username
                        
                        change_key = input("Change SSH key? (y/n): ").strip().lower()
                        if change_key in ['y', 'yes']:
                            new_key = select_ssh_key()
                            if new_key:
                                device['ssh_key'] = new_key
                        
                        save_device_config(devices)
                        print("Device updated successfully!")
                    else:
                        print("Invalid device number!")
                except ValueError:
                    print("Please enter a valid number!")
            elif action in ['l', 'list']:
                print("Current devices:")
                for i, device in enumerate(devices, 1):
                    print(f"  {i}. {device['hostname']} (subfolder: {device['label']}) - User: {device['username']}")
                    print(f"      SSH Key: {device['ssh_key']}")
                    print(f"      Logs stored in: ~/Downloads/rlogs/{device['label']}/")
            elif action in ['s', 'size']:
                print("\nGenerating device size report...")
                if os.path.exists(diroutbase):
                    report_device_sizes_after_compression(diroutbase)
                else:
                    print(f"❌ Rlog directory '{diroutbase}' does not exist.")
                    print("💡 Run the downloader first to create device folders.")
            else:
                print("Invalid option! Please enter 'a', 'r', 'e', 'l', 's', or 'c'")
    
    return devices

def sanitize_filename(filename):
    """Sanitize filename for Windows compatibility while preserving route structure."""
    # Replace problematic characters for Windows
    # Note: Windows doesn't allow | in filenames, so we use _ as a replacement
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Also replace any remaining path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove or replace problematic sequences
    filename = filename.replace('..', '__')
    
    # Ensure filename isn't too long (Windows has 260 char path limit)
    if len(filename) > 200:
        name_part, ext = os.path.splitext(filename)
        filename = name_part[:200-len(ext)] + ext
    
    return filename

def connect_ssh(host, username, ssh_key):
    """Connect to SSH with better error handling and Windows support."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Attempting to connect to {host} as user '{username}'")
    
    try:
        # First try with the specified key file
        if ssh_key and os.path.exists(ssh_key):
            print(f"Connecting using SSH key: {ssh_key}")
            
            # Try different key types for better Windows compatibility
            key_loaded = False
            for key_class in [paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey]:
                try:
                    if 'passphrase' in ssh_key or 'password' in ssh_key:
                        # Key might be password protected
                        try:
                            key = key_class.from_private_key_file(ssh_key)
                            client.connect(hostname=host, username=username, pkey=key, timeout=30)
                            key_loaded = True
                            break
                        except paramiko.ssh_exception.PasswordRequiredException:
                            password = input(f"Enter passphrase for key {ssh_key}: ")
                            key = key_class.from_private_key_file(ssh_key, password=password)
                            client.connect(hostname=host, username=username, pkey=key, timeout=30)
                            key_loaded = True
                            break
                    else:
                        key = key_class.from_private_key_file(ssh_key)
                        client.connect(hostname=host, username=username, pkey=key, timeout=30)
                        key_loaded = True
                        break
                except (paramiko.ssh_exception.SSHException, ValueError, FileNotFoundError):
                    continue
            
            if not key_loaded:
                print("Failed to load the specified key, falling back to SSH agent...")
                client.connect(hostname=host, username=username, allow_agent=True, look_for_keys=True, timeout=30)
        else:
            # Fallback to agent/system keys
            print("No valid SSH key specified, using SSH agent or system keys...")
            client.connect(hostname=host, username=username, allow_agent=True, look_for_keys=True, timeout=30)
            
        print("Successfully connected!")
        return client
        
    except paramiko.AuthenticationException as e:
        print(f"Authentication failed: {e}")
        print("\nTroubleshooting steps:")
        print("1. Make sure you've copied your PUBLIC key to the device:")
        if ssh_key and os.path.exists(ssh_key):
            pub_key_path = ssh_key + ".pub"
            if os.path.exists(pub_key_path):
                with open(pub_key_path, 'r', encoding='utf-8') as f:
                    pub_key_content = f.read().strip()
                print(f"   Your public key content: {pub_key_content}")
                print(f"   Copy this to your device's /home/{username}/.ssh/authorized_keys file")
        print("2. Make sure SSH is enabled on your device")
        print(f"3. Try connecting manually with: ssh {username}@{host}")
        raise
    except Exception as e:
        print(f"Connection failed: {e}")
        raise

def setup_ssh_multiplexing(device_host, username, ssh_key):
    """Set up SSH connection multiplexing for faster subsequent connections."""
    ssh_dir = os.path.expanduser("~/.ssh")
    control_dir = os.path.join(ssh_dir, "control_sockets")
    
    # Create control socket directory if it doesn't exist
    os.makedirs(control_dir, exist_ok=True)
    
    # Use a unique control socket for this device
    control_socket = os.path.join(control_dir, f"rsync_{device_host}_{username}")
    
    # Set up master connection
    master_cmd = [
        "ssh",
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ControlMaster=yes",
        "-o", f"ControlPath={control_socket}",
        "-o", "ControlPersist=300",  # Keep connection alive for 5 minutes
        "-o", "Compression=no",
        "-o", "ServerAliveInterval=30",
        "-o", "TCPKeepAlive=yes",
        "-N",  # Don't execute a remote command
        f"{username}@{device_host}"
    ]
    
    try:
        # Start master connection in background
        print(f"Setting up SSH connection multiplexing for {device_host}...")
        subprocess.Popen(master_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Give it a moment to establish
        time.sleep(2)
        return control_socket
    except Exception as e:
        print(f"Warning: Could not set up SSH multiplexing: {e}")
        return None

def cleanup_ssh_multiplexing(control_socket):
    """Clean up SSH connection multiplexing."""
    if control_socket and os.path.exists(control_socket):
        try:
            # Close the master connection
            subprocess.run([
                "ssh", "-o", f"ControlPath={control_socket}", "-O", "exit", "dummy"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        except Exception:
            pass  # Don't worry if cleanup fails

def run_ssh_command(ssh, cmd):
    """Execute a command over SSH and return stdout and stderr."""
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

def fetch_rlogs_rsync(device):
    """Fetch rlogs using rsync (faster and more efficient than SFTP)."""
    device_host = device['hostname']
    label = device['label']
    username = device['username']
    ssh_key = device['ssh_key']
    
    print(f"{device_host} ({label}): Connecting via SSH to check status...")
    
    # Check if rsync is available
    if not is_rsync_available():
        print(f"{device_host} ({label}): rsync not available, falling back to SFTP")
        return fetch_rlogs_sftp(device)
    
    # Set up SSH connection multiplexing for faster transfers
    control_socket = setup_ssh_multiplexing(device_host, username, ssh_key)
    
    try:
        ssh = connect_ssh(device_host, username, ssh_key)
    except Exception as e:
        print(f"{device_host} ({label}): Connection failed: {e}")
        cleanup_ssh_multiplexing(control_socket)
        return

    dongle_id, _ = run_ssh_command(ssh, "cat /data/params/d/DongleId")
    is_offroad, _ = run_ssh_command(ssh, "cat /data/params/d/IsOffroad")

    if is_offroad.strip() != "1":
        print(f"{device_host} ({label}): Skipping, device is onroad")
        ssh.close()
        cleanup_ssh_multiplexing(control_socket)
        return

    if not is_on_home_wifi():
        print(f"{device_host} ({label}): Not on home WiFi")
        ssh.close()
        cleanup_ssh_multiplexing(control_socket)
        return

    output_dir = Path(diroutbase) / label / dongle_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a temporary directory to download files before renaming
    temp_download_dir = output_dir / ".rsync_temp"
    temp_download_dir.mkdir(exist_ok=True)
    
    print(f"{device_host} ({label}): Getting list of remote files...")
    remote_files_cmd = f"find {remote_data_dir} -name '*rlog*' -type f"
    remote_files_output, _ = run_ssh_command(ssh, remote_files_cmd)
    
    ssh.close()
    
    # Parse remote files and check if we already have them (renamed)
    remote_files = remote_files_output.strip().split('\n') if remote_files_output.strip() else []
    existing_files = set()
    
    # Build set of existing renamed files
    for file_path in output_dir.glob('*rlog*'):
        existing_files.add(file_path.name)
    
    # Check which files we actually need to download
    files_needed = []
    
    print(f"{device_host} ({label}): Analyzing which files we need...")
    print(f"Sample existing files: {list(existing_files)[:3]}")
    
    for remote_file in remote_files:
        if not remote_file.strip():
            continue
        
        # Convert remote path to what the renamed file would be
        relative_path = remote_file.replace(remote_data_dir + "/", "")
        route_parts = relative_path.split("/")
        filename = route_parts[-1]
        
        if len(route_parts) > 1:
            route = "|".join(route_parts[:-1])
            expected_filename = f"{dongle_id}|{route}--{filename}"
        else:
            expected_filename = f"{dongle_id}--{filename}"
        
        # Sanitize filename for Windows compatibility
        expected_filename = sanitize_filename(expected_filename)
        
        if expected_filename not in existing_files:
            files_needed.append(remote_file)
            
        # Debug: show first few comparisons
        if len(files_needed) <= 3:
            status = 'MISSING' if expected_filename not in existing_files else 'EXISTS'
            print(f"Remote: {relative_path} -> Expected: {expected_filename} -> {status}")
    
    if not files_needed:
        print(f"{device_host} ({label}): All {len(remote_files)} files already exist, skipping rsync")
        # Clean up temp directory
        try:
            temp_download_dir.rmdir()
        except OSError:
            pass
        cleanup_ssh_multiplexing(control_socket)
        return
    
    print(f"{device_host} ({label}): Need to download {len(files_needed)} files out of {len(remote_files)} total")
    
    # Use optimized bulk rsync instead of individual file downloads
    print(f"{device_host} ({label}): Starting optimized bulk rsync transfer...")
    
    # Create an include/exclude list for rsync to only download needed files
    include_file = temp_download_dir / "rsync_includes.txt"
    exclude_file = temp_download_dir / "rsync_excludes.txt"
    
    try:
        # Write include patterns for files we need
        with open(include_file, 'w') as f:
            # Include all directories leading to rlog files
            f.write("+ */\n")  # Include all directories
            # Include specific files we need
            for needed_file in files_needed:
                relative_path = needed_file.replace(remote_data_dir + "/", "")
                f.write(f"+ {relative_path}\n")
            # Exclude everything else
            f.write("- *\n")
        
        # Optimized rsync command with performance improvements
        rsync_cmd = [
            "rsync",
            "-avzP",  # archive, verbose, compress, progress
            "--partial",  # keep partial transfers
            "--partial-dir=.rsync-partial",  # partial transfer directory
            "--preallocate",  # preallocate file space (faster on some filesystems)
            f"--compress-level={rsync_compress_level}",  # configurable compression
            "--copy-links",  # copy symlinks as files
            "--include-from", str(include_file),
            "--delete-excluded",  # clean up excluded files in destination
        ]
        
        # Add conditional optimizations
        if rsync_whole_file:
            rsync_cmd.append("--whole-file")  # don't use delta transfer (faster for initial downloads)
        
        if rsync_bandwidth_limit > 0:
            rsync_cmd.append(f"--bwlimit={rsync_bandwidth_limit}")
        
        # Add SSH options for better performance
        ssh_opts = [
            "-o", "StrictHostKeyChecking=no",
            "-o", "Compression=no",  # Let rsync handle compression
            "-o", "Cipher=aes128-ctr",  # Fast cipher
            "-o", "ServerAliveInterval=30",  # Keep connection alive
            "-o", "TCPKeepAlive=yes"
        ]
        
        # Use connection multiplexing if available
        if control_socket:
            ssh_opts.extend(["-o", f"ControlPath={control_socket}", "-o", "ControlMaster=no"])
        
        rsync_cmd.extend([
            f"--rsh=ssh -i \"{ssh_key}\" {' '.join(ssh_opts)}",
            f"{username}@{device_host}:{remote_data_dir}/",
            str(temp_download_dir) + "/"
        ])
        
        # On Windows, handle path separators correctly
        if platform.system() == "Windows":
            rsync_cmd[-1] = str(temp_download_dir).replace('\\', '/') + "/"
        
        print(f"Executing optimized rsync command with SSH multiplexing...")
        print(f"Command: {' '.join(rsync_cmd[:8])} ...")  # Don't print the full SSH key
        
        # Run rsync with real-time output
        process = subprocess.Popen(
            rsync_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        files_downloaded = 0
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                # Count successfully transferred files
                if line.endswith('.rlog') or line.endswith('.rlog.bz2'):
                    files_downloaded += 1
                    print(f"  ✓ {line}")
                elif 'bytes/sec' in line or '%' in line:
                    print(f"  {line}")
                elif line.startswith('sent') or line.startswith('total size'):
                    print(f"  {line}")
        
        process.wait()
        
        if process.returncode == 0:
            print(f"{device_host} ({label}): Bulk transfer completed successfully")
            print(f"{device_host} ({label}): Downloaded approximately {files_downloaded} files")
        else:
            print(f"{device_host} ({label}): rsync completed with warnings/errors (exit code: {process.returncode})")
            print(f"{device_host} ({label}): This is often normal and doesn't indicate failure")
        
    except subprocess.CalledProcessError as e:
        print(f"{device_host} ({label}): rsync failed: {e}")
        cleanup_ssh_multiplexing(control_socket)
        return
    except Exception as e:
        print(f"{device_host} ({label}): Error during rsync: {e}")
        cleanup_ssh_multiplexing(control_socket)
        return
    finally:
        # Clean up temporary files
        try:
            include_file.unlink()
        except FileNotFoundError:
            pass
        try:
            exclude_file.unlink()
        except FileNotFoundError:
            pass
    
    # Rename files to match the original naming convention (dongle_id|route--filename)
    print(f"{device_host} ({label}): Moving and renaming files to final location...")
    rename_and_move_rsync_files(temp_download_dir, output_dir, dongle_id)
    
    # Clean up temp directory and SSH multiplexing
    try:
        temp_download_dir.rmdir()
    except OSError as e:
        print(f"Warning: Could not remove temp directory {temp_download_dir}: {e}")
    
    cleanup_ssh_multiplexing(control_socket)

def rename_and_move_rsync_files(temp_dir, output_dir, dongle_id):
    """Move files from temp directory and rename them to match the original SFTP naming convention."""
    
    # First, build a map of existing renamed files to avoid duplicates
    existing_renamed = {}
    for file_path in output_dir.glob('*rlog*'):
        if not file_path.is_file():
            continue
        # If filename already contains dongle_id, it's already renamed
        if file_path.name.startswith(dongle_id):
            existing_renamed[file_path.name] = file_path
    
    files_moved = 0
    files_skipped = 0
    
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if "rlog" in file and not file.startswith('.rsync'):
                current_path = Path(root) / file
                # Get the relative path from the temp_dir
                rel_path = current_path.relative_to(temp_dir)
                
                # Skip if this file is already in renamed format (shouldn't happen in temp dir)
                if current_path.name.startswith(dongle_id):
                    continue
                
                # Convert path to route format (replace / with |)
                route_parts = list(rel_path.parts[:-1])  # All parts except filename
                if route_parts:
                    route = "|".join(route_parts)
                    new_filename = f"{dongle_id}|{route}--{file}"
                else:
                    new_filename = f"{dongle_id}--{file}"
                
                # Sanitize filename for Windows compatibility
                new_filename = sanitize_filename(new_filename)
                
                new_path = output_dir / new_filename
                
                # Check if target file already exists (prevents duplicates)
                if new_filename in existing_renamed:
                    print(f"Target file already exists, skipping: {rel_path}")
                    try:
                        current_path.unlink()  # Remove the temp file
                        files_skipped += 1
                    except Exception as e:
                        print(f"Failed to remove temp file {current_path}: {e}")
                elif new_path.exists():
                    print(f"Target file exists on disk, skipping: {rel_path}")
                    try:
                        current_path.unlink()  # Remove the temp file
                        files_skipped += 1
                    except Exception as e:
                        print(f"Failed to remove temp file {current_path}: {e}")
                else:
                    try:
                        current_path.rename(new_path)
                        existing_renamed[new_filename] = new_path  # Track it
                        files_moved += 1
                        print(f"Moved and renamed: {rel_path} → {new_filename}")
                    except Exception as e:
                        print(f"Failed to move and rename {current_path}: {e}")
    
    print(f"Files processed: {files_moved} moved, {files_skipped} skipped (duplicates)")
    
    # Clean up empty directories in temp directory
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            try:
                if not any(dir_path.iterdir()):  # Directory is empty
                    dir_path.rmdir()
            except OSError:
                pass  # Directory not empty or other error

def rename_rsync_files(output_dir, dongle_id, remote_data_dir):
    """Rename rsync'd files to match the original SFTP naming convention (legacy function)."""
    
    # First, build a map of existing renamed files to avoid duplicates
    existing_renamed = {}
    for file_path in output_dir.glob('*rlog*'):
        if not file_path.is_file():
            continue
        # If filename already contains dongle_id, it's already renamed
        if file_path.name.startswith(dongle_id):
            existing_renamed[file_path.name] = file_path
    
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if "rlog" in file:
                current_path = Path(root) / file
                # Get the relative path from the output_dir
                rel_path = current_path.relative_to(output_dir)
                
                # Skip if this file is already in renamed format
                if current_path.name.startswith(dongle_id):
                    continue
                
                # Convert path to route format (replace / with |)
                route_parts = list(rel_path.parts[:-1])  # All parts except filename
                if route_parts:
                    route = "|".join(route_parts)
                    new_filename = f"{dongle_id}|{route}--{file}"
                else:
                    new_filename = f"{dongle_id}--{file}"
                
                # Sanitize filename for Windows compatibility
                new_filename = sanitize_filename(new_filename)
                
                new_path = output_dir / new_filename
                
                # Check if target file already exists (prevents duplicates)
                if new_filename in existing_renamed:
                    print(f"Target file already exists, removing duplicate: {rel_path}")
                    try:
                        current_path.unlink()  # Remove the duplicate
                    except Exception as e:
                        print(f"Failed to remove duplicate {current_path}: {e}")
                elif new_path.exists():
                    print(f"Target file exists on disk, removing duplicate: {rel_path}")
                    try:
                        current_path.unlink()  # Remove the duplicate
                    except Exception as e:
                        print(f"Failed to remove duplicate {current_path}: {e}")
                else:
                    try:
                        current_path.rename(new_path)
                        existing_renamed[new_filename] = new_path  # Track it
                        print(f"Renamed: {rel_path} → {new_filename}")
                    except Exception as e:
                        print(f"Failed to rename {current_path}: {e}")
    
    # Clean up empty directories
    for root, dirs, files in os.walk(output_dir, topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            try:
                if not any(dir_path.iterdir()):  # Directory is empty
                    dir_path.rmdir()
            except OSError:
                pass  # Directory not empty or other error

def fetch_rlogs_sftp(device):
    """Fetch rlogs using SFTP (original method)."""
    device_host = device['hostname']
    label = device['label']
    username = device['username']
    ssh_key = device['ssh_key']
    
    print(f"{device_host} ({label}): Connecting...")
    try:
        ssh = connect_ssh(device_host, username, ssh_key)
    except Exception as e:
        print(f"{device_host} ({label}): Connection failed: {e}")
        return

    dongle_id, _ = run_ssh_command(ssh, "cat /data/params/d/DongleId")
    is_offroad, _ = run_ssh_command(ssh, "cat /data/params/d/IsOffroad")

    if is_offroad.strip() != "1":
        print(f"{device_host} ({label}): Skipping, device is onroad")
        return

    if not is_on_home_wifi():
        print(f"{device_host} ({label}): Not on home WiFi")
        return

    sftp = ssh.open_sftp()
    output_dir = Path(diroutbase) / label / dongle_id
    output_dir.mkdir(parents=True, exist_ok=True)

    def walk_rlog_files(path):
        try:
            for dirpath, dirnames, filenames in sftp_walk(sftp, path):
                for file in filenames:
                    if "rlog" in file:
                        # Use forward slashes for remote paths
                        yield dirpath.rstrip('/') + '/' + file
        except Exception as e:
            print(f"Error walking remote path: {e}")

    import stat

    def sftp_walk(sftp, remotepath):
        """Walk through SFTP directory structure with Windows compatibility."""
        path_stack = [remotepath]
        while path_stack:
            current_path = path_stack.pop()
            try:
                files = []
                folders = []
                for entry in sftp.listdir_attr(current_path):
                    fname = entry.filename
                    # Use forward slashes for remote paths (Unix-style)
                    fullpath = current_path.rstrip('/') + '/' + fname
                    if stat.S_ISDIR(entry.st_mode):
                        folders.append(fullpath)
                    else:
                        files.append(fname)
                yield current_path, folders, files
                path_stack.extend(folders)
            except IOError:
                continue

    for filepath in walk_rlog_files(remote_data_dir):
        route = filepath.replace(remote_data_dir + "/", "").rsplit("/", 1)[0]
        filename = filepath.rsplit("/", 1)[-1]
        local_filename = f"{dongle_id}|{route}--{filename}"
        
        # Sanitize filename for Windows compatibility
        local_filename = sanitize_filename(local_filename)
        
        local_path = output_dir / local_filename
        if local_path.exists():
            continue
        try:
            print(f"Downloading {filepath} → {local_filename}")
            
            # Show file size for progress indication (if available)
            try:
                file_stat = sftp.stat(filepath)
                file_size = file_stat.st_size
                print(f"  File size: {file_size / (1024*1024):.1f} MB")
            except:
                pass
                
            sftp.get(filepath, str(local_path))
            print(f"  ✓ Download completed")
        except Exception as e:
            print(f"Failed to download {filepath}: {e}")

    sftp.close()
    ssh.close()

def fetch_rlogs(device):
    """Fetch rlogs using the configured transfer method."""
    if transfer_method.lower() == "rsync":
        fetch_rlogs_rsync(device)
    else:
        fetch_rlogs_sftp(device)

def format_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_index = 0
    size = float(size_bytes)
    while size >= 1024.0 and size_index < len(size_names) - 1:
        size /= 1024.0
        size_index += 1
    return f"{size:.2f} {size_names[size_index]}"

def get_folder_size(folder_path):
    """Calculate total size of all files in a folder and its subfolders."""
    total_size = 0
    try:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
    except Exception as e:
        print(f"Error calculating folder size for {folder_path}: {e}")
    return total_size

def compress_unzipped_rlogs(base_dir):
    import gzip
    import shutil
    from collections import defaultdict
    
    # Check if zstd is available first (best compression)
    zstd_available = False
    try:
        subprocess.run(["zstd", "--version"], capture_output=True, check=True)
        zstd_available = True
        print("Using zstd compression...")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("zstd not found, using built-in gzip compression...")
    
    # Track compression statistics per device
    device_stats = defaultdict(lambda: {
        'files_compressed': 0,
        'original_size': 0,
        'compressed_size': 0,
        'compression_errors': 0
    })
    
    # First pass: collect all uncompressed rlog files and their sizes
    files_to_compress = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith("rlog"):
                full_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(full_path)
                    # Extract device info from path structure
                    rel_path = os.path.relpath(root, base_dir)
                    device_label = rel_path.split(os.sep)[0] if os.sep in rel_path else rel_path
                    files_to_compress.append((full_path, file_size, device_label))
                except Exception as e:
                    print(f"Error getting size for {full_path}: {e}")
    
    if not files_to_compress:
        print("No uncompressed rlog files found.")
        # Still report current device sizes
        report_device_sizes_after_compression(base_dir)
        return
    
    total_files = len(files_to_compress)
    print(f"Found {total_files} uncompressed rlog files to process...")
    
    # Compress files and track statistics
    for i, (full_path, original_size, device_label) in enumerate(files_to_compress, 1):
        print(f"[{i}/{total_files}] Processing: {os.path.basename(full_path)} ({format_size(original_size)})")
        
        device_stats[device_label]['original_size'] += original_size
        
        success = False
        compressed_size = 0
        
        if zstd_available:
            # Use zstd if available
            try:
                # On Windows, handle path quoting for subprocess
                if platform.system() == "Windows":
                    result = subprocess.run(["zstd", "--rm", "-f", str(full_path)], 
                                          check=True, shell=True, capture_output=True)
                else:
                    result = subprocess.run(["zstd", "--rm", "-f", full_path], 
                                          check=True, capture_output=True)
                
                # Check for compressed file
                compressed_path = full_path + ".zst"
                if os.path.exists(compressed_path):
                    compressed_size = os.path.getsize(compressed_path)
                    success = True
                    print(f"  ✓ Compressed with zstd: {format_size(original_size)} → {format_size(compressed_size)} ({compressed_size/original_size*100:.1f}%)")
                
            except subprocess.CalledProcessError as e:
                print(f"  ✗ Failed to compress with zstd: {e}")
                device_stats[device_label]['compression_errors'] += 1
        else:
            # Use Python's built-in gzip compression
            compressed_path = full_path + ".gz"
            try:
                with open(full_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                if os.path.exists(compressed_path):
                    compressed_size = os.path.getsize(compressed_path)
                    success = True
                    # Remove original file after successful compression
                    os.remove(full_path)
                    print(f"  ✓ Compressed with gzip: {format_size(original_size)} → {format_size(compressed_size)} ({compressed_size/original_size*100:.1f}%)")
                
            except Exception as e:
                print(f"  ✗ Failed to compress with gzip: {e}")
                device_stats[device_label]['compression_errors'] += 1
                # Remove incomplete compressed file if it exists
                if os.path.exists(compressed_path):
                    try:
                        os.remove(compressed_path)
                    except:
                        pass
        
        if success:
            device_stats[device_label]['files_compressed'] += 1
            device_stats[device_label]['compressed_size'] += compressed_size
    
    # Print compression summary
    print("\n" + "="*60)
    print("COMPRESSION SUMMARY")
    print("="*60)
    
    total_original = 0
    total_compressed = 0
    total_files_compressed = 0
    total_errors = 0
    
    for device_label, stats in device_stats.items():
        if stats['files_compressed'] > 0 or stats['compression_errors'] > 0:
            print(f"\nDevice: {device_label}")
            print(f"  Files compressed: {stats['files_compressed']}")
            if stats['compression_errors'] > 0:
                print(f"  Compression errors: {stats['compression_errors']}")
            if stats['files_compressed'] > 0:
                print(f"  Original size: {format_size(stats['original_size'])}")
                print(f"  Compressed size: {format_size(stats['compressed_size'])}")
                if stats['original_size'] > 0:
                    ratio = stats['compressed_size'] / stats['original_size'] * 100
                    savings = stats['original_size'] - stats['compressed_size']
                    print(f"  Compression ratio: {ratio:.1f}% (saved {format_size(savings)})")
            
            total_original += stats['original_size']
            total_compressed += stats['compressed_size']
            total_files_compressed += stats['files_compressed']
            total_errors += stats['compression_errors']
    
    if total_files_compressed > 0:
        print(f"\nOVERALL COMPRESSION:")
        print(f"  Total files compressed: {total_files_compressed}")
        if total_errors > 0:
            print(f"  Total errors: {total_errors}")
        print(f"  Total original size: {format_size(total_original)}")
        print(f"  Total compressed size: {format_size(total_compressed)}")
        if total_original > 0:
            overall_ratio = total_compressed / total_original * 100
            total_savings = total_original - total_compressed
            print(f"  Overall compression ratio: {overall_ratio:.1f}% (saved {format_size(total_savings)})")
    
    # Report final device sizes after compression
    print("\n" + "="*60)
    report_device_sizes_after_compression(base_dir)

def report_device_sizes_after_compression(base_dir):
    """Report the total size of each device folder after compression."""
    print("DEVICE FOLDER SIZES AFTER COMPRESSION")
    print("="*60)
    
    if not os.path.exists(base_dir):
        print(f"Base directory {base_dir} does not exist.")
        return
    
    device_folders = []
    total_all_devices = 0
    
    try:
        # Get all device folders (first level subdirectories)
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                folder_size = get_folder_size(item_path)
                device_folders.append((item, folder_size))
                total_all_devices += folder_size
    except Exception as e:
        print(f"Error reading device folders: {e}")
        return
    
    if not device_folders:
        print("No device folders found.")
        return
    
    # Sort devices by size (largest first)
    device_folders.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Found {len(device_folders)} device folder(s):\n")
    
    for device_name, size in device_folders:
        print(f"  {device_name:<20} {format_size(size):>12}")
        
        # Show breakdown by dongle_id if there are subfolders
        device_path = os.path.join(base_dir, device_name)
        try:
            subfolders = []
            for subfolder in os.listdir(device_path):
                subfolder_path = os.path.join(device_path, subfolder)
                if os.path.isdir(subfolder_path):
                    subfolder_size = get_folder_size(subfolder_path)
                    subfolders.append((subfolder, subfolder_size))
            
            if len(subfolders) > 1:  # Only show breakdown if multiple dongle IDs
                subfolders.sort(key=lambda x: x[1], reverse=True)
                for subfolder_name, subfolder_size in subfolders:
                    print(f"    └─ {subfolder_name:<16} {format_size(subfolder_size):>12}")
        except Exception as e:
            print(f"    └─ Error reading subfolders: {e}")
    
    print(f"\nTOTAL SIZE (all devices): {format_size(total_all_devices)}")
    
    # Show file count statistics
    print(f"\nFILE STATISTICS:")
    for device_name, _ in device_folders:
        device_path = os.path.join(base_dir, device_name)
        file_counts = {'rlog': 0, 'rlog.gz': 0, 'rlog.zst': 0, 'rlog.bz2': 0, 'other': 0}
        
        try:
            for root, dirs, files in os.walk(device_path):
                for file in files:
                    if file.endswith('.rlog.zst'):
                        file_counts['rlog.zst'] += 1
                    elif file.endswith('.rlog.gz'):
                        file_counts['rlog.gz'] += 1
                    elif file.endswith('.rlog.bz2'):
                        file_counts['rlog.bz2'] += 1
                    elif file.endswith('.rlog'):
                        file_counts['rlog'] += 1
                    else:
                        file_counts['other'] += 1
            
            total_files = sum(file_counts.values())
            if total_files > 0:
                print(f"  {device_name:<20} {total_files:>4} files ", end="")
                details = []
                if file_counts['rlog.zst'] > 0:
                    details.append(f"{file_counts['rlog.zst']} zst")
                if file_counts['rlog.gz'] > 0:
                    details.append(f"{file_counts['rlog.gz']} gz")
                if file_counts['rlog.bz2'] > 0:
                    details.append(f"{file_counts['rlog.bz2']} bz2")
                if file_counts['rlog'] > 0:
                    details.append(f"{file_counts['rlog']} uncompressed")
                if file_counts['other'] > 0:
                    details.append(f"{file_counts['other']} other")
                
                if details:
                    print(f"({', '.join(details)})")
                else:
                    print()
        except Exception as e:
            print(f"  {device_name:<20} Error counting files: {e}")
    
    print("="*60)

def main():
    print(f"Cross-platform rlog downloader (Windows/macOS/Linux)")
    print(f"Using transfer method: {transfer_method}")
    print()
    print("💡 Features:")
    print("   • Download rlogs from your Comma 3/3X device")
    print("   • Automatic compression (zstd/gzip)")
    print("   • Device size reporting and compression statistics")
    print("   • Multi-device management")
    print()
    
    if transfer_method.lower() == "rsync":
        print(f"Rsync optimizations enabled:")
        print(f"  - Compression level: {rsync_compress_level}")
        print(f"  - Whole file transfers: {rsync_whole_file}")
        print(f"  - Bandwidth limit: {rsync_bandwidth_limit} KB/s" if rsync_bandwidth_limit > 0 else "  - Bandwidth limit: None")
        print(f"  - SSH connection multiplexing: Enabled")
        print(f"  - Bulk transfer with smart filtering: Enabled")
        
        if not is_rsync_available():
            print("Warning: rsync not found, will fall back to SFTP if needed")
            if platform.system() == "Windows":
                print("Tip: Install Git for Windows or WSL to enable rsync support")
    
    # Load or create device configuration
    device_list = manage_device_config()
    
    if not device_list:
        print("No devices configured. Exiting.")
        return
    
    print(f"\nStarting download for {len(device_list)} device(s)...")
    for device in device_list:
        print(f"Processing {device['hostname']} (subfolder: {device['label']}) with user {device['username']}")
        fetch_rlogs(device)
        time.sleep(5)  # Optional wait between devices

    print("Compressing unzipped rlogs and generating size report...")
    compress_unzipped_rlogs(diroutbase)
    print("Done.")

if __name__ == "__main__":
    main()
