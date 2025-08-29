# Comma 3/3X Route Log Downloader

This script connects to your Comma 3/3X device and downloads your driving logs (rlogs) to a local directory. It automatically handles file organization, prevents duplicate downloads, and supports compression for storage efficiency.

**Note**: The main `download_rlog_files.py` script now includes full Windows support. The separate `download_rlog_files_windows.py` is no longer needed but kept for reference.

## Features

- **Cross-platform support**: Works on Windows, macOS, and Linux
- **Multiple transfer methods**: Supports both rsync (faster) and SFTP
- **Optimized rsync performance**: 
  - Bulk transfers with smart file filtering
  - SSH connection multiplexing for faster connections
  - Configurable compression levels and bandwidth limiting
  - Optimized SSH cipher selection for speed
  - Partial transfer support with resume capability
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

**Note**: Both setup scripts will automatically create a Python virtual environment if the standard pip install fails, and provide convenient wrapper scripts (`run_rlog_downloader.bat` on Windows, `run_rlog_downloader.sh` on Unix) for easy execution.

### Manual Setup

1. **Clone or download this repository**

2. **Install Python dependencies**:
   
   **Most systems:**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Windows:**
   ```cmd
   # Option 1: Standard install
   pip install -r requirements.txt
   
   # Option 2: Virtual environment (if standard fails)
   python -m venv venv
   venv\Scripts\activate.bat
   pip install -r requirements.txt
   REM Run script with: python download_rlog_files.py
   REM Deactivate with: venv\Scripts\deactivate.bat
   ```
   
   **Ubuntu 22.04+/Debian 12+ (externally managed environment):**
   ```bash
   # Option 1: Use virtual environment (recommended)
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   # Run script with: python download_rlog_files.py
   # Deactivate with: deactivate
   
   # Option 2: System packages
   sudo apt-get install python3-paramiko
   
   # Option 3: pipx
   pipx install --include-deps paramiko
   ```
   
   **Or install manually:**
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

**Windows:**
```cmd
python download_rlog_files.py
REM Or if you used setup_windows.bat with virtual env:
run_rlog_downloader.bat
```

**macOS/Linux:**
```bash
python download_rlog_files.py
# Or if you used setup_unix.sh with virtual env:
./run_rlog_downloader.sh
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
- **rsync** (default): Faster, more efficient, resume support, with advanced optimizations
- **sftp**: More compatible, works everywhere paramiko works

Edit the configuration variables in the script:
```python
transfer_method = "rsync"  # or "sftp"

# Rsync optimization settings (only used when transfer_method = "rsync")
rsync_compress_level = 1  # 1-9, lower = faster but larger, higher = slower but smaller
rsync_parallel_transfers = False  # Enable experimental parallel transfers
rsync_bandwidth_limit = 0  # KB/s, 0 = no limit (use for slower connections)
rsync_whole_file = True  # Use whole-file transfers (faster for initial sync)
```

### Rsync Performance Optimizations
The script includes several rsync optimizations:

1. **SSH Connection Multiplexing**: Reuses SSH connections for faster subsequent transfers
2. **Bulk Transfers**: Downloads all needed files in a single rsync operation instead of individual transfers
3. **Smart File Filtering**: Uses include/exclude patterns to only transfer new files
4. **Optimized SSH Ciphers**: Uses fast AES-128-CTR cipher for better performance
5. **Configurable Compression**: Adjustable compression levels to balance speed vs. bandwidth
6. **Partial Transfer Support**: Resumes interrupted transfers automatically
7. **Bandwidth Limiting**: Optional bandwidth control for slower connections

These optimizations can provide 2-5x faster transfer speeds compared to the original individual file approach.

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

**"externally-managed-environment" (Linux)**
- This is common on Ubuntu 22.04+ and Debian 12+
- Use the setup script which creates a virtual environment automatically
- Or manually: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- Alternative: `sudo apt-get install python3-paramiko` or `pipx install --include-deps paramiko`

**"Failed to install dependencies" (Windows)**
- The setup script will automatically try creating a virtual environment
- Or manually: `python -m venv venv && venv\Scripts\activate.bat && pip install -r requirements.txt`
- Make sure you have Python installed with pip support

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
