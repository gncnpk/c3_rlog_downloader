# Comma 3/3X Route Log Downloader

This script connects to your Comma 3/3X device and downloads your driving logs (rlogs) to a local directory. It automatically handles file organization, prevents duplicate downloads, and supports compression for storage efficiency.

**Note**: The main `download_rlog_files.py` script now includes full Windows support. The separate `download_rlog_files_windows.py` is no longer needed but kept for reference.

## Features

- **Cross-platform support**: Works on Windows, macOS, and Linux
- **Multiple transfer methods**: Supports both rsync (faster) and SFTP
- **Smart deduplication**: Only downloads new files that haven't been downloaded yet
- **Automatic compression**: Supports zstd and gzip compression to save disk space
- **Device management**: Store and manage multiple device configurations
- **Windows compatibility**: Handles Windows path limitations and file naming requirements
- **Progress tracking**: Shows download progress and file sizes

## Prerequisites

1. **SSH access to your Comma device** - Follow the [official SSH setup guide](https://github.com/commaai/openpilot/wiki/SSH)
2. **Python 3.6 or later**
3. **Required Python packages** (see Installation)

### Optional but Recommended
- **rsync** (for faster transfers on Unix-like systems)
- **zstd** (for better compression)

## Installation

### Quick Setup (Recommended)

**Windows:**
```cmd
setup_windows.bat
```

**macOS/Linux:**
```bash
chmod +x setup_unix.sh
./setup_unix.sh
```

### Manual Setup

1. **Clone or download this repository**
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
   Or install manually:
   ```bash
   pip install paramiko
   ```

3. **Install optional tools** (recommended):
   
   **On Windows:**
   - For rsync: Install [Git for Windows](https://git-scm.com/download/win) or [WSL](https://docs.microsoft.com/en-us/windows/wsl/install)
   - For zstd: Download from [Facebook's zstd releases](https://github.com/facebook/zstd/releases)
   
   **On macOS:**
   ```bash
   brew install rsync zstd
   ```
   
   **On Linux:**
   ```bash
   sudo apt-get install rsync zstd
   # or
   sudo yum install rsync zstd
   ```

## Setup

### Step 1: SSH Key Setup
Make sure you have SSH keys set up for your Comma device:

1. **Generate SSH key** (if you don't have one):
   ```bash
   ssh-keygen -t ed25519 -C "your-email@example.com"
   ```

2. **Copy public key to your device**:
   ```bash
   ssh-copy-id comma@YOUR_DEVICE_IP
   ```

3. **Test SSH connection**:
   ```bash
   ssh comma@YOUR_DEVICE_IP
   ```

### Step 2: Configure Your Device
1. **Connect your Comma device to your home WiFi**
2. **Find your device's IP address** (usually in your router's admin panel or shown on the device)
3. **Ensure your device is in "offroad" mode** when running the script

## Usage

### Basic Usage
Simply run the script:
```bash
python download_rlog_files.py
```

On first run, you'll be guided through:
1. **Device setup**: Add your device's IP address and choose a subfolder name (called "label" in the interface)
2. **SSH key selection**: The script will find and help you select the right SSH key
3. **Configuration saving**: Your settings are saved for future runs

### Configuration Management
The script provides an interactive menu to:
- **Add new devices** (if you have multiple Comma devices)
- **Edit existing device settings**
- **Remove devices**
- **List all configured devices**

### File Organization
Downloaded files are organized as:
```
~/Downloads/rlogs/
├── device_subfolder_1/
│   └── dongle_id/
│       ├── dongle_id|route_name--segment--0--rlog.bz2
│       ├── dongle_id|route_name--segment--1--rlog.bz2
│       └── ...
├── device_subfolder_2/
│   └── dongle_id/
│       └── ...
```

## Configuration

### Transfer Methods
You can choose between:
- **rsync** (default): Faster, more efficient, resume support
- **sftp**: More compatible, works everywhere paramiko works

Edit the `transfer_method` variable in the script:
```python
transfer_method = "rsync"  # or "sftp"
```

### Directories
- **Download location**: `~/Downloads/rlogs` (customizable via `diroutbase`)
- **Remote data directory**: `/data/media/0/realdata` (usually doesn't change)
- **Config file**: `devices_config.json` (stored next to the script)

## Troubleshooting

### Common Issues

**"SSH connection failed"**
- Verify your device is connected to WiFi
- Check that SSH is enabled on your device
- Ensure your SSH key is properly set up
- Try connecting manually: `ssh comma@YOUR_DEVICE_IP`

**"rsync not found" (Windows)**
- Install Git for Windows or use WSL
- The script will automatically fall back to SFTP

**"Permission denied"**
- Make sure your SSH key has the correct permissions
- On Unix: `chmod 600 ~/.ssh/id_ed25519`

**"Device is onroad"**
- The script only downloads when the device is in "offroad" mode for safety
- Park your car and wait for the device to go offroad

### File Naming on Windows
The script automatically handles Windows file naming restrictions by:
- Replacing invalid characters (`<>:"|?*`) with underscores
- Limiting filename length to prevent path issues
- Converting path separators appropriately

## Advanced Usage

### Multiple Devices
You can configure multiple Comma devices and the script will download from all of them:
```json
{
  "devices": [
    {
      "hostname": "10.0.0.5",
      "label": "main_car",
      "username": "comma",
      "ssh_key": "/path/to/ssh/key"
    },
    {
      "hostname": "10.0.0.6", 
      "label": "second_car",
      "username": "comma",
      "ssh_key": "/path/to/ssh/key"
    }
  ]
}
```

**Note**: The "label" field specifies the subfolder name where each device's logs will be stored.

### Custom SSH Keys
The script will automatically find SSH keys, but you can specify custom paths during device setup.

### Compression Options
- **zstd**: Best compression and speed (if available)
- **gzip**: Good compression, always available
- **None**: Skip compression to save processing time

## Contributing

Feel free to submit issues, suggestions, or pull requests to improve this tool!

## License

This project is based on tools from the [sunnypilot](https://github.com/mmmorks/sunnypilot) project.

## Support

If you need help:
1. Check the troubleshooting section above
2. Ensure you have the latest version of the script
3. Test your SSH connection manually
4. Open an issue with detailed error messages
