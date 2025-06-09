# python version of https://github.com/mmmorks/sunnypilot/blob/staging-merged/tools/tuning/rlog_copy_from_device_then_zip1.sh
# downloads rlogs of your device, using a previously saved ssh key thing
import os
import time
import subprocess
import paramiko
from pathlib import Path
import io
import stat
import platform

# ========= MODIFY THESE If you want to =========
diroutbase = os.path.expanduser("~/Downloads/rlogs")
device_car_list = [
    ("10.0.0.5", "comma"),  # (hostname/IP, subfolder name) - this is ip of your device
]
# These -probably- don't change
ssh_username = "comma"
remote_data_dir = "/data/media/0/realdata" # pretty sure this wont change
# SSH key path for Windows
ssh_key_path = os.path.expanduser("~/.ssh/id_ed25519")

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

def load_ssh_key():
    """Load the SSH private key"""
    try:
        if not os.path.exists(ssh_key_path):
            print(f"SSH key not found at {ssh_key_path}")
            # Also check for .pub file to see if keys were generated
            pub_key_path = ssh_key_path + ".pub"
            if os.path.exists(pub_key_path):
                print(f"Public key found at {pub_key_path}")
                print("Make sure you've copied the public key to your device's authorized_keys file")
            return None
        
        print(f"Attempting to load SSH key from {ssh_key_path}")
        
        # Try to load as Ed25519 key first
        try:
            key = paramiko.Ed25519Key.from_private_key_file(ssh_key_path)
            print(f"Successfully loaded Ed25519 key from {ssh_key_path}")
            return key
        except paramiko.ssh_exception.PasswordRequiredException:
            # Key is password protected
            password = input(f"Enter passphrase for key {ssh_key_path}: ")
            key = paramiko.Ed25519Key.from_private_key_file(ssh_key_path, password=password)
            print(f"Successfully loaded password-protected Ed25519 key from {ssh_key_path}")
            return key
        except paramiko.ssh_exception.SSHException as e:
            print(f"Failed to load as Ed25519 key: {e}")
            # Try RSA key as fallback
            try:
                key = paramiko.RSAKey.from_private_key_file(ssh_key_path)
                print(f"Successfully loaded RSA key from {ssh_key_path}")
                return key
            except paramiko.ssh_exception.PasswordRequiredException:
                password = input(f"Enter passphrase for key {ssh_key_path}: ")
                key = paramiko.RSAKey.from_private_key_file(ssh_key_path, password=password)
                print(f"Successfully loaded password-protected RSA key from {ssh_key_path}")
                return key
            except Exception as rsa_e:
                print(f"Failed to load as RSA key: {rsa_e}")
                return None
    except Exception as e:
        print(f"Failed to load SSH key: {e}")
        return None

def connect_ssh(host):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Attempting to connect to {host} as user '{ssh_username}'")
    
    # Load the private key
    key = load_ssh_key()
    
    try:
        if key:
            print("Connecting using loaded private key...")
            # Connect using the loaded private key
            client.connect(hostname=host, username=ssh_username, pkey=key, timeout=30)
            print("Successfully connected using private key!")
        else:
            # Fallback to agent/system keys
            print("No private key loaded, falling back to SSH agent or system keys...")
            client.connect(hostname=host, username=ssh_username, allow_agent=True, look_for_keys=True, timeout=30)
            print("Successfully connected using SSH agent/system keys!")
            
    except paramiko.AuthenticationException as e:
        print(f"Authentication failed: {e}")
        print("\nTroubleshooting steps:")
        print("1. Make sure you've copied your PUBLIC key to the device:")
        pub_key_path = ssh_key_path + ".pub"
        if os.path.exists(pub_key_path):
            with open(pub_key_path, 'r') as f:
                pub_key_content = f.read().strip()
            print(f"   Your public key content: {pub_key_content}")
            print(f"   Copy this to your device's /home/{ssh_username}/.ssh/authorized_keys file")
        print("2. Make sure SSH is enabled on your device")
        print("3. Try connecting manually with: ssh comma@{host}")
        raise
    except Exception as e:
        print(f"Connection failed: {e}")
        raise
    
    return client

def run_ssh_command(ssh, cmd):
    """Run SSH command and return stdout, stderr"""
    print(f"Running command: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout_result = stdout.read().decode().strip()
    stderr_result = stderr.read().decode().strip()
    
    if stderr_result:
        print(f"Command stderr: {stderr_result}")
    if stdout_result:
        print(f"Command stdout: {stdout_result}")
    
    return stdout_result, stderr_result

def sanitize_filename(filename):
    """Sanitize filename for Windows compatibility"""
    # Replace problematic characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Also replace any remaining path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    return filename

def sftp_walk(sftp, remotepath):
    """Walk through SFTP directory structure"""
    path_stack = [remotepath]
    while path_stack:
        current_path = path_stack.pop()
        try:
            print(f"Checking directory: {current_path}")
            files = []
            folders = []
            for entry in sftp.listdir_attr(current_path):
                fname = entry.filename
                fullpath = os.path.join(current_path, fname).replace('\\', '/')  # Normalize path separators
                if stat.S_ISDIR(entry.st_mode):
                    folders.append(fullpath)
                else:
                    files.append(fname)
            
            print(f"Found {len(files)} files and {len(folders)} folders in {current_path}")
            yield current_path, folders, files
            path_stack.extend(folders)
        except IOError as e:
            print(f"Error accessing {current_path}: {e}")
            continue

def walk_rlog_files(sftp, path):
    """Walk through directories and find rlog files"""
    rlog_count = 0
    try:
        for dirpath, dirnames, filenames in sftp_walk(sftp, path):
            for file in filenames:
                if "rlog" in file:
                    rlog_count += 1
                    filepath = os.path.join(dirpath, file).replace('\\', '/')
                    print(f"Found rlog file #{rlog_count}: {filepath}")
                    yield filepath
    except Exception as e:
        print(f"Error walking remote path: {e}")
    
    print(f"Total rlog files found: {rlog_count}")

def fetch_rlogs(device_host, label):
    print(f"\n{'='*50}")
    print(f"{device_host} ({label}): Starting rlog fetch...")
    print(f"{'='*50}")
    
    try:
        ssh = connect_ssh(device_host)
    except Exception as e:
        print(f"{device_host} ({label}): Connection failed: {e}")
        return

    # Get dongle ID
    print(f"\n{device_host} ({label}): Getting dongle ID...")
    dongle_id, dongle_err = run_ssh_command(ssh, "cat /data/params/d/DongleId")
    if dongle_err or not dongle_id:
        print(f"{device_host} ({label}): Could not get dongle ID. Error: {dongle_err}")
        ssh.close()
        return
    print(f"Dongle ID: {dongle_id}")

    # Check if device is offroad
    print(f"\n{device_host} ({label}): Checking if device is offroad...")
    is_offroad, offroad_err = run_ssh_command(ssh, "cat /data/params/d/IsOffroad")
    print(f"IsOffroad result: '{is_offroad}' (should be '1')")
    
    if is_offroad.strip() != "1":
        print(f"{device_host} ({label}): Skipping, device is onroad (IsOffroad = '{is_offroad}')")
        ssh.close()
        return

    # Check WiFi (optional - comment out if you want to download regardless)
    # if not is_on_home_wifi():
    #     print(f"{device_host} ({label}): Not on home WiFi")
    #     ssh.close()
    #     return

    # Check if remote directory exists
    print(f"\n{device_host} ({label}): Checking remote directory: {remote_data_dir}")
    dir_check, dir_err = run_ssh_command(ssh, f"ls -la {remote_data_dir}")
    if dir_err and "No such file" in dir_err:
        print(f"{device_host} ({label}): Remote directory {remote_data_dir} does not exist!")
        ssh.close()
        return

    # Set up SFTP
    print(f"\n{device_host} ({label}): Setting up SFTP...")
    try:
        sftp = ssh.open_sftp()
        print("SFTP connection established")
    except Exception as e:
        print(f"Failed to establish SFTP connection: {e}")
        ssh.close()
        return

    # Create output directory
    output_dir = Path(diroutbase) / label / dongle_id
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Find and download rlog files
    print(f"\n{device_host} ({label}): Searching for rlog files...")
    downloaded_count = 0
    skipped_count = 0
    
    for filepath in walk_rlog_files(sftp, remote_data_dir):
        # Extract route and filename
        relative_path = filepath.replace(remote_data_dir + "/", "")
        if "/" in relative_path:
            route = relative_path.rsplit("/", 1)[0]
            filename = relative_path.rsplit("/", 1)[-1]
        else:
            route = ""
            filename = relative_path
            
        # Use underscore instead of pipe for Windows compatibility and sanitize
        local_filename = f"{dongle_id}_{route}--{filename}" if route else f"{dongle_id}_{filename}"
        local_filename = sanitize_filename(local_filename)
        local_path = output_dir / local_filename
        
        if local_path.exists():
            print(f"Skipping existing file: {local_filename}")
            skipped_count += 1
            continue

        try:
            print(f"Downloading: {filepath} → {local_filename}")
            
            # Get file size for progress indication
            try:
                file_stat = sftp.stat(filepath)
                file_size = file_stat.st_size
                print(f"  File size: {file_size / (1024*1024):.1f} MB")
            except:
                file_size = 0
                
            sftp.get(filepath, str(local_path))
            downloaded_count += 1
            print(f"  ✓ Download completed")
            
        except Exception as e:
            print(f"  ✗ Failed to download {filepath}: {e}")

    print(f"\n{device_host} ({label}): Download summary:")
    print(f"  Downloaded: {downloaded_count} files")
    print(f"  Skipped: {skipped_count} files")
    
    sftp.close()
    ssh.close()

def compress_unzipped_rlogs(base_dir):
    import gzip
    import shutil
    
    print(f"\nCompressing rlog files in {base_dir}...")
    
    # Check if zstd is available first (best compression)
    zstd_available = False
    try:
        subprocess.run(["zstd", "--version"], capture_output=True, check=True)
        zstd_available = True
        print("Using zstd compression...")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("zstd not found, using built-in gzip compression...")
    
    compressed_count = 0
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith("rlog"):
                full_path = os.path.join(root, file)
                
                if zstd_available:
                    # Use zstd if available
                    print(f"Compressing with zstd: {full_path}")
                    try:
                        subprocess.run(["zstd", "--rm", "-f", full_path], check=True)
                        compressed_count += 1
                    except subprocess.CalledProcessError as e:
                        print(f"Failed to compress {full_path}: {e}")
                else:
                    # Use Python's built-in gzip compression
                    compressed_path = full_path + ".gz"
                    print(f"Compressing with gzip: {full_path} → {compressed_path}")
                    try:
                        with open(full_path, 'rb') as f_in:
                            with gzip.open(compressed_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        # Remove original file after successful compression
                        os.remove(full_path)
                        compressed_count += 1
                    except Exception as e:
                        print(f"Failed to compress {full_path}: {e}")
                        # Remove incomplete compressed file if it exists
                        if os.path.exists(compressed_path):
                            os.remove(compressed_path)
    
    print(f"Compressed {compressed_count} files")

def main():
    print("Starting rlog downloader...")
    print(f"Output base directory: {diroutbase}")
    print(f"SSH key path: {ssh_key_path}")
    
    # Check if SSH key exists
    if not os.path.exists(ssh_key_path):
        print(f"SSH key not found at {ssh_key_path}")
        print("Please ensure your SSH key is at the correct location or update ssh_key_path variable")
        return
    
    for host, label in device_car_list:
        fetch_rlogs(host, label)
    
    print("\nCompressing unzipped rlogs...")
    compress_unzipped_rlogs(diroutbase)
    print("Done.")

if __name__ == "__main__":
    main()
