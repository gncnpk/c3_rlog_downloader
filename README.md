# Comma 3/3X Route Log Management Suite

Download and manage driving logs (rlogs) from your Comma 3/3X device with automatic compression and Google Drive backup.

## 🚀 Quick Start

```bash
# Clone and run
git clone https://github.com/gncnpk/c3_rlog_downloader.git
cd c3_rlog_downloader
python launcher.py
```

## 📁 What You Get

- **Download rlogs** from your Comma device via SSH
- **Automatic compression** (zstd/gzip) to save space
- **Upload to Google Drive** with smart folder management
- **Device management** for multiple cars
- **Size reporting** and compression statistics

## 🛠️ Requirements

1. **SSH access** to your Comma device ([setup guide](https://github.com/commaai/openpilot/wiki/SSH))
2. **Python 3.6+**
3. **RClone** for Google Drive uploads (optional)

The launcher will help you install dependencies and configure everything.

## 📋 Usage

### Unified Launcher (Recommended)
```bash
python launcher.py
```

### Individual Scripts
```bash
python download.py  # Download and compress rlogs
python upload.py    # Upload to Google Drive
```

## 📁 File Organization

```
rlogs/
├── device1/
│   └── dongle_id/
│       ├── dongle_id|route--0--rlog.gz
│       └── dongle_id|route--1--rlog.gz
└── device2/
    └── dongle_id/
        └── ...
```

## ⚙️ Configuration

### Multiple Devices
The download script manages multiple devices with an interactive menu:
- Add/remove/edit devices
- SSH key management
- Size reporting
- Device-specific folders

### Transfer Options
- **rsync** (faster, recommended)
- **sftp** (more compatible)

### Google Drive
RClone automatically splits folders at 2GB for Google Drive compatibility.

## 🔧 Troubleshooting

**SSH Connection Issues:**
- Verify device is on WiFi and offroad
- Test manually: `ssh comma@YOUR_DEVICE_IP`
- Check SSH key permissions: `chmod 600 ~/.ssh/your_key`

**Missing Dependencies:**
- Windows: Install Git for Windows (includes rsync)
- Linux: `sudo apt install rsync zstd`
- macOS: `brew install rsync zstd`

**RClone Issues:**
- Install: `winget install Rclone.Rclone` (Windows) or `brew install rclone` (macOS)
- Configure: `rclone config` (choose Google Drive, name it 'gdrive')

## 📚 Project Structure

```
c3_rlog_downloader/
├── launcher.py      # Main unified interface
├── download.py      # Route log downloader
├── upload.py        # Google Drive uploader
├── requirements.txt # Python dependencies
└── README.md        # This file
```

---

**Quick workflow:** `python launcher.py` → Setup → Download → Upload → Done! 🎉
