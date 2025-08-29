#!/bin/bash

echo "RClone Google Drive Upload Setup for Linux"
echo "=========================================="
echo

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo $ID
    elif [ -f /etc/redhat-release ]; then
        echo "rhel"
    elif [ -f /etc/debian_version ]; then
        echo "debian"
    else
        echo "unknown"
    fi
}

# Check if rclone is installed
echo "Checking if rclone is installed..."
if command_exists rclone; then
    echo "✅ rclone is already installed"
    rclone version | head -1
else
    echo "❌ rclone not found. Installing..."
    
    # Detect distribution and install accordingly
    DISTRO=$(detect_distro)
    
    case $DISTRO in
        ubuntu|debian|pop|mint)
            echo "Detected Debian/Ubuntu-based system"
            echo "Installing rclone via curl script (recommended)..."
            curl https://rclone.org/install.sh | sudo bash
            ;;
        fedora)
            echo "Detected Fedora system"
            echo "Installing rclone via dnf..."
            sudo dnf install -y rclone
            ;;
        centos|rhel)
            echo "Detected RHEL/CentOS system"
            echo "Installing rclone via curl script..."
            curl https://rclone.org/install.sh | sudo bash
            ;;
        arch|manjaro)
            echo "Detected Arch-based system"
            echo "Installing rclone via pacman..."
            sudo pacman -S --noconfirm rclone
            ;;
        opensuse*)
            echo "Detected openSUSE system"
            echo "Installing rclone via zypper..."
            sudo zypper install -y rclone
            ;;
        *)
            echo "Unknown distribution. Installing via curl script..."
            curl https://rclone.org/install.sh | sudo bash
            ;;
    esac
    
    # Verify installation
    if command_exists rclone; then
        echo "✅ rclone installed successfully"
        rclone version | head -1
    else
        echo "❌ rclone installation failed"
        echo "Please install manually:"
        echo "  1. Download from: https://rclone.org/downloads/"
        echo "  2. Or use: curl https://rclone.org/install.sh | sudo bash"
        echo "  3. Make sure rclone is in your PATH"
        exit 1
    fi
fi

echo
echo "Checking rclone configuration..."
if rclone listremotes | grep -q "gdrive:"; then
    echo "✅ Google Drive remote 'gdrive' is already configured"
else
    echo "❌ Google Drive remote not configured"
    echo
    echo "To configure rclone for Google Drive:"
    echo "1. Run: rclone config"
    echo "2. Choose 'n' for new remote"
    echo "3. Name it 'gdrive'"
    echo "4. Choose number for 'Google Drive' (usually 22)"
    echo "5. Leave client_id and client_secret blank (press Enter)"
    echo "6. Choose '1' for full access scope"
    echo "7. Leave root_folder_id blank (press Enter)"
    echo "8. Leave service_account_file blank (press Enter)"
    echo "9. Choose 'n' for advanced config"
    echo "10. Choose 'y' for auto config (will open browser)"
    echo "11. Choose 'n' for team drive"
    echo "12. Choose 'y' to confirm"
    echo "13. Choose 'q' to quit config"
    echo
    read -p "Would you like to configure it now? (y/n): " configure
    if [[ $configure =~ ^[Yy]$ ]]; then
        rclone config
    fi
fi

echo
echo "Checking Python requirements..."
if command_exists python3; then
    echo "✅ Python 3 is available"
    python3 --version
else
    echo "❌ Python 3 not found"
    echo "Installing Python 3..."
    
    case $DISTRO in
        ubuntu|debian|pop|mint)
            sudo apt update && sudo apt install -y python3 python3-pip
            ;;
        fedora)
            sudo dnf install -y python3 python3-pip
            ;;
        centos|rhel)
            sudo yum install -y python3 python3-pip
            ;;
        arch|manjaro)
            sudo pacman -S --noconfirm python python-pip
            ;;
        opensuse*)
            sudo zypper install -y python3 python3-pip
            ;;
        *)
            echo "Please install Python 3 manually for your distribution"
            exit 1
            ;;
    esac
fi

echo
echo "Setup complete!"
echo
echo "To upload your rlogs:"
echo "  python3 upload_to_google_drive_rclone.py"
echo
echo "Features:"
echo "- Automatically splits device folders to stay under 2GB"
echo "- Skips files already uploaded"
echo "- Uses parallel transfers for speed"
echo "- Shows progress and statistics"
echo
echo "Make sure to run the rlog downloader first:"
echo "  python3 download_rlog_files.py"
echo
