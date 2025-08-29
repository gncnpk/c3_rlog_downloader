#!/bin/bash

echo "Comma Route Log Downloader - Unix Setup"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "Error: Python is not installed"
        echo "Please install Python 3.6 or later"
        exit 1
    else
        PYTHON_CMD=python
    fi
else
    PYTHON_CMD=python3
fi

echo "Python found!"
$PYTHON_CMD --version

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    if ! command -v pip &> /dev/null; then
        echo "Error: pip is not available"
        echo "Please install pip"
        exit 1
    else
        PIP_CMD=pip
    fi
else
    PIP_CMD=pip3
fi

echo "Installing Python dependencies..."
$PIP_CMD install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

# Check for optional tools
echo
echo "Checking for optional tools..."

if command -v rsync &> /dev/null; then
    echo "✓ rsync found - fast transfers available"
else
    echo "⚠ rsync not found - will use SFTP (slower)"
    echo "  Install with: sudo apt-get install rsync (Ubuntu/Debian)"
    echo "  Install with: brew install rsync (macOS)"
fi

if command -v zstd &> /dev/null; then
    echo "✓ zstd found - best compression available"
else
    echo "⚠ zstd not found - will use gzip compression"
    echo "  Install with: sudo apt-get install zstd (Ubuntu/Debian)"
    echo "  Install with: brew install zstd (macOS)"
fi

echo
echo "Setup completed successfully!"
echo "You can now run: $PYTHON_CMD download_rlog_files.py"
