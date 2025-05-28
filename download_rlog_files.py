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

def connect_ssh(host):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # use the pre-loaded key from the private_key_str
    client.connect(hostname=host, username=ssh_username, allow_agent=True, look_for_keys=True)
    #client.connect(hostname=host, username=ssh_username, pkey=key)
    return client

def run_ssh_command(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

def fetch_rlogs(device_host, label):
    print(f"{device_host} ({label}): Connecting...")
    try:
        ssh = connect_ssh(device_host)
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
                        yield os.path.join(dirpath, file)
        except Exception as e:
            print(f"Error walking remote path: {e}")

    import stat

    def sftp_walk(sftp, remotepath):
        path_stack = [remotepath]
        while path_stack:
            current_path = path_stack.pop()
            try:
                files = []
                folders = []
                for entry in sftp.listdir_attr(current_path):
                    fname = entry.filename
                    fullpath = os.path.join(current_path, fname)
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
        local_path = output_dir / local_filename
        if local_path.exists():
            continue
        try:
            print(f"Downloading {filepath} → {local_filename}")
            sftp.get(filepath, str(local_path))
        except Exception as e:
            print(f"Failed to download {filepath}: {e}")

    sftp.close()
    ssh.close()

def compress_unzipped_rlogs(base_dir):
    import gzip
    import shutil
    
    # Check if zstd is available first (best compression)
    zstd_available = False
    try:
        subprocess.run(["zstd", "--version"], capture_output=True, check=True)
        zstd_available = True
        print("Using zstd compression...")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("zstd not found, using built-in gzip compression...")
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith("rlog"):
                full_path = os.path.join(root, file)
                
                if zstd_available:
                    # Use zstd if available
                    print(f"Compressing with zstd: {full_path}")
                    try:
                        subprocess.run(["zstd", "--rm", "-f", full_path], check=True)
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
                    except Exception as e:
                        print(f"Failed to compress {full_path}: {e}")
                        # Remove incomplete compressed file if it exists
                        if os.path.exists(compressed_path):
                            os.remove(compressed_path)

def main():
    for host, label in device_car_list:
        fetch_rlogs(host, label)
        time.sleep(5)  # Optional wait between devices

    print("Compressing unzipped rlogs...")
    compress_unzipped_rlogs(diroutbase)
    print("Done.")

if __name__ == "__main__":
    main()
