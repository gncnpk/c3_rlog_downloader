# Comma 3/3X Route Log Management Suite

This comprehensive toolkit connects to your Comma 3/3X device to download driving logs (rlogs) and upload them to Google Drive for backup and organization. It handles file organization, prevents duplicates, supports compression, and maintains cloud backups with intelligent folder size management.

## 🚀 Features

### 📥 **Route Log Downloader** (`download_rlog_files.py`)
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

### ☁️ **Google Drive Upload** (`upload_to_google_drive_rclone.py`)
- **RClone-powered uploads**: Fast, reliable transfers using native rclone binary
- **Intelligent folder management**: Automatically splits device folders to stay under 2GB
- **Smart organization**: Maintains folder structure (device/dongle_id/) in Google Drive
- **Duplicate prevention**: Skips files that already exist on Google Drive
- **Parallel transfers**: Uses multiple concurrent uploads for speed
- **Progress tracking**: Real-time upload progress and transfer statistics
- **Resumable uploads**: Handles interrupted transfers gracefully
- **Cross-platform**: Works on Windows, macOS, and Linux

## 📁 File Organization

**Local Structure:**
```
rlogs/
├── device_label_1/
│   └── dongle_id/
│       ├── dongle_id|route_name--segment--0--rlog.bz2
│       ├── dongle_id|route_name--segment--1--rlog.bz2
│       └── ...
└── device_label_2/
    └── dongle_id/
        └── ...
```

**Google Drive Structure:**
```
Google Drive/rlogs/
├── device_label_1/
│   ├── dongle_id/           # < 2GB
│   ├── dongle_id_part2/     # < 2GB  
│   └── dongle_id_part3/     # < 2GB
└── device_label_2/
    ├── dongle_id/           # < 2GB
    └── dongle_id_part2/     # < 2GB
```

## 📋 Prerequisites

### For Route Log Downloading
1. **SSH access to your Comma device** - Follow the [official SSH setup guide](https://github.com/commaai/openpilot/wiki/SSH)
2. **Python 3.6 or later**
3. **Required Python packages** (see Installation)

### For Google Drive Upload
1. **RClone installed and configured** for Google Drive access
2. **Google Drive account** with sufficient storage space

### Optional but Recommended
- **rsync** (for faster transfers on Unix-like systems)
- **zstd** (for better compression)

## 🛠️ Installation & Setup

### Quick Setup

#### **Windows**
```cmd
# Setup rlog downloader
setup_windows.bat

# Setup Google Drive upload
setup_google_drive.bat
```

#### **macOS/Linux**
```bash
# Setup rlog downloader
chmod +x setup_unix.sh
./setup_unix.sh

# Setup Google Drive upload
chmod +x setup_google_drive.sh
./setup_google_drive.sh
```

### Step-by-Step Setup

#### 1. **Rlog Downloader Setup**
**Install Python dependencies:**
   
   **Most systems:**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Windows:**
   ```cmd
   pip install -r requirements.txt
   ```
   
   **Ubuntu 22.04+/Debian 12+ (externally managed environment):**
   ```bash
   # Option 1: Use virtual environment (recommended)
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Option 2: System packages
   sudo apt-get install python3-paramiko
   ```

**Install optional tools (recommended):**
   
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

#### 2. **Google Drive Upload Setup**

**Install RClone:**

**Windows:**
```cmd
# Option 1: winget (Windows 10+)
winget install Rclone.Rclone

# Option 2: Chocolatey
choco install rclone

# Option 3: Manual download from https://rclone.org/downloads/
```

**macOS:**
```bash
brew install rclone
```

**Linux:**
```bash
# Most distributions
curl https://rclone.org/install.sh | sudo bash

# Ubuntu/Debian
sudo apt update && sudo apt install rclone

# Fedora
sudo dnf install rclone

# Arch Linux
sudo pacman -S rclone
```

**Configure RClone for Google Drive:**
```bash
rclone config
```
Follow prompts:
1. Choose 'n' for new remote
2. Name it 'gdrive'
3. Choose 'Google Drive'
4. Follow authentication steps

## 🎯 Usage

### Download RLogs from Comma Device

**Windows:**
```cmd
python download_rlog_files.py
# Or if using setup script with virtual env:
run_rlog_downloader.bat
```

**macOS/Linux:**
```bash
python3 download_rlog_files.py
# Or if using setup script with virtual env:
./run_rlog_downloader.sh
```

On first run, you'll be guided through:
1. **Device setup**: Add your device's IP address and choose a subfolder name
2. **SSH key selection**: The script will find and help you select the right SSH key
3. **Configuration saving**: Your settings are saved for future runs

### Upload RLogs to Google Drive

After downloading rlogs locally:

```bash
# Windows
python upload_to_google_drive_rclone.py

# macOS/Linux  
python3 upload_to_google_drive_rclone.py
```

The upload script will:
1. **Check for existing files** and skip duplicates
2. **Monitor folder sizes** and create new subfolders when approaching 2GB
3. **Upload files in parallel** for maximum speed
4. **Show progress** with transfer statistics

### Complete Workflow

```bash
# 1. Download rlogs from your Comma device
python3 download_rlog_files.py

# 2. Upload to Google Drive for backup
python3 upload_to_google_drive_rclone.py
```

## ⚙️ Configuration

### Device Management
The rlog downloader provides an interactive menu to:
- **Add new devices** (if you have multiple Comma devices)
- **Edit existing device settings**
- **Remove devices**
- **List all configured devices**

### Transfer Methods (Rlog Downloader)
You can choose between:
- **rsync** (default): Faster, more efficient, resume support, with advanced optimizations
- **sftp**: More compatible, works everywhere paramiko works

Edit the configuration variables in `download_rlog_files.py`:
```python
transfer_method = "rsync"  # or "sftp"

# Rsync optimization settings (only used when transfer_method = "rsync")
rsync_compress_level = 1  # 1-9, lower = faster but larger, higher = slower but smaller
rsync_bandwidth_limit = 0  # KB/s, 0 = no limit (use for slower connections)
rsync_whole_file = True  # Use whole-file transfers (faster for initial sync)
```

### Google Drive Upload Settings
Edit configuration variables in `upload_to_google_drive_rclone.py`:
```python
REMOTE_NAME = "gdrive"              # Name of your rclone remote
GOOGLE_DRIVE_FOLDER = "rlogs"       # Main folder name in Google Drive  
MAX_FOLDER_SIZE_GB = 2.0           # Maximum size per device folder in GB
```

### Rsync Performance Optimizations
The downloader includes several rsync optimizations:

1. **SSH Connection Multiplexing**: Reuses SSH connections for faster subsequent transfers
2. **Bulk Transfers**: Downloads all needed files in a single rsync operation instead of individual transfers
3. **Smart File Filtering**: Uses include/exclude patterns to only transfer new files
4. **Optimized SSH Ciphers**: Uses fast AES-128-CTR cipher for better performance
5. **Configurable Compression**: Adjustable compression levels to balance speed vs. bandwidth
6. **Partial Transfer Support**: Resumes interrupted transfers automatically
7. **Bandwidth Limiting**: Optional bandwidth control for slower connections

These optimizations can provide 2-5x faster transfer speeds compared to individual file transfers.

### Directory Structure
- **Download location**: `./rlogs/` (relative to script directory)
- **Remote data directory**: `/data/media/0/realdata` (usually doesn't change)
- **Config file**: `devices_config.json` (stored next to the script)

## 🔧 Troubleshooting

### SSH Connection Issues

**"SSH connection failed"**
- Verify your device is connected to WiFi
- Check that SSH is enabled on your device
- Ensure your SSH key is properly set up
- Try connecting manually: `ssh comma@YOUR_DEVICE_IP`

**"Permission denied"**
- Make sure your SSH key has the correct permissions
- On Unix: `chmod 600 ~/.ssh/id_ed25519`

### Installation Issues

**"rsync not found" (Windows)**
- Install Git for Windows or use WSL
- The script will automatically fall back to SFTP

**"externally-managed-environment" (Linux)**
- This is common on Ubuntu 22.04+ and Debian 12+
- Use the setup script which creates a virtual environment automatically
- Or manually: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- Alternative: `sudo apt-get install python3-paramiko`

**"Failed to install dependencies" (Windows)**
- The setup script will automatically try creating a virtual environment
- Or manually: `python -m venv venv && venv\Scripts\activate.bat && pip install -r requirements.txt`

### Google Drive Upload Issues

**"rclone not found"**
- Install rclone using the setup script or manually
- Make sure rclone is in your system PATH

**"Google Drive remote not configured"**
- Run `rclone config` to set up Google Drive access
- Make sure to name your remote 'gdrive' (or update the script configuration)

**"Upload failed" or "Connection timeout"**
- Check your internet connection
- Verify rclone configuration: `rclone lsd gdrive:`
- Try uploading a single file manually: `rclone copy test.txt gdrive:`

### General Issues

**"Device is onroad"**
- The script only downloads when the device is in "offroad" mode for safety
- Park your car and wait for the device to go offroad

**File Naming on Windows**
- The script automatically handles Windows file naming restrictions by:
  - Replacing invalid characters (`<>:"|?*`) with underscores
  - Limiting filename length to prevent path issues
  - Converting path separators appropriately

## 🔥 Advanced Usage

### Multiple Devices
Configure multiple Comma devices for batch processing:
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

### Custom RClone Configuration
For advanced rclone setups, you can customize the upload script:
```python
# Custom remote name
REMOTE_NAME = "my_gdrive"

# Custom folder structure
GOOGLE_DRIVE_FOLDER = "comma_logs/archive"

# Smaller folder size limits
MAX_FOLDER_SIZE_GB = 1.5
```

### Automation Scripts
Create automated workflows:

**Windows (batch file):**
```cmd
@echo off
echo Starting rlog backup workflow...
python download_rlog_files.py
python upload_to_google_drive_rclone.py
echo Backup complete!
```

**Linux/macOS (shell script):**
```bash
#!/bin/bash
echo "Starting rlog backup workflow..."
python3 download_rlog_files.py
python3 upload_to_google_drive_rclone.py
echo "Backup complete!"
```

### Compression Options
- **zstd**: Best compression and speed (if available)
- **gzip**: Good compression, always available
- **None**: Skip compression to save processing time

## 🎯 Benefits of This Setup

### 🚀 **Performance**
- **RClone vs API**: 3-5x faster uploads compared to Google Drive API
- **Parallel transfers**: Multiple simultaneous uploads
- **Rsync optimization**: 2-5x faster downloads with bulk transfers

### 🗂️ **Organization**
- **Consistent structure**: Same organization locally and in cloud
- **Smart folder splitting**: Automatic 2GB folder management
- **No duplicates**: Intelligent file deduplication

### 🔒 **Reliability**
- **Resumable transfers**: Handles network interruptions
- **Error handling**: Automatic retries and fallbacks
- **Cross-platform**: Works consistently across operating systems

### 💾 **Storage Efficiency**
- **Compression support**: zstd/gzip compression for local storage
- **Cloud optimization**: Efficient folder size management for Google Drive

## 📚 Project Structure

```
rlog_aggregation/
├── download_rlog_files.py          # Main rlog downloader script
├── upload_to_google_drive_rclone.py # Google Drive upload script
├── requirements.txt                 # Python dependencies
├── setup_windows.bat               # Windows setup script
├── setup_unix.sh                   # macOS/Linux setup script  
├── setup_google_drive.bat          # Windows rclone setup
├── setup_google_drive.sh           # Linux rclone setup
├── run_rlog_downloader.bat         # Windows launcher (created by setup)
├── run_rlog_downloader.sh          # Unix launcher (created by setup)
├── devices_config.json             # Device configuration (created on first run)
├── rlogs/                          # Downloaded rlog files
│   ├── device1/
│   │   └── dongle_id/
│   └── device2/
│       └── dongle_id/
└── README.md                       # This file
```

## 🤝 Contributing

Feel free to submit issues, suggestions, or pull requests to improve this toolkit!

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on multiple platforms if possible
5. Submit a pull request

### Reporting Issues
When reporting issues, please include:
- Operating system and version
- Python version
- Full error messages
- Steps to reproduce

## 📄 License

This project is based on tools from the [sunnypilot](https://github.com/mmmorks/sunnypilot) project.

## 🆘 Support

If you need help:
1. Check the troubleshooting section above
2. Ensure you have the latest version of the scripts
3. Test your SSH connection manually
4. For rclone issues, test with `rclone lsd gdrive:`
5. Open an issue with detailed error messages

## 🚗 Related Projects

- [OpenPilot](https://github.com/commaai/openpilot) - The main comma.ai driving assistance software
- [SunnyPilot](https://github.com/mmmorks/sunnypilot) - Enhanced OpenPilot fork
- [RClone](https://rclone.org/) - Command line program to manage files on cloud storage
