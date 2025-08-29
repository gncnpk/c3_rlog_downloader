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

# Check if we're in an externally managed environment
if $PIP_CMD install --dry-run paramiko 2>&1 | grep -q "externally-managed-environment"; then
    echo "Detected externally managed Python environment (common on Ubuntu 22.04+)"
    echo "Creating virtual environment for better compatibility..."
    
    # Create virtual environment
    if ! $PYTHON_CMD -m venv venv; then
        echo "Failed to create virtual environment. Installing python3-venv..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y python3-venv python3-full
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-venv
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3-venv
        else
            echo "Please install python3-venv manually for your distribution"
            exit 1
        fi
        
        # Try creating venv again
        if ! $PYTHON_CMD -m venv venv; then
            echo "Still failed to create virtual environment"
            exit 1
        fi
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo
        echo "✓ Dependencies installed successfully in virtual environment!"
        
        # Create wrapper script
        cat > run_rlog_downloader.sh << 'EOF'
#!/bin/bash
# Simple wrapper script to run the rlog downloader with virtual environment
cd "$(dirname "$0")"
if [ -d "venv" ]; then
    source venv/bin/activate
    python download_rlog_files.py "$@"
    deactivate
else
    python download_rlog_files.py "$@"
fi
EOF
        chmod +x run_rlog_downloader.sh
        
        echo "  Created wrapper script 'run_rlog_downloader.sh'"
        echo "  To run the script:"
        echo "    ./run_rlog_downloader.sh"
        echo "  Or manually:"
        echo "    source venv/bin/activate"
        echo "    python download_rlog_files.py"
        echo "    deactivate  # when done"
    else
        echo "Failed to install dependencies in virtual environment"
        exit 1
    fi
else
    # Normal pip install
    $PIP_CMD install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo "✓ Dependencies installed successfully!"
    else
        echo "Error: Failed to install dependencies"
        echo "You may need to:"
        echo "  1. Create a virtual environment: python3 -m venv venv && source venv/bin/activate"
        echo "  2. Install system packages: sudo apt-get install python3-paramiko"
        echo "  3. Use pipx: pipx install --include-deps paramiko"
        exit 1
    fi
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
if [ -d "venv" ]; then
    echo "Virtual environment created. To run the script:"
    echo "  ./run_rlog_downloader.sh  # uses wrapper script"
    echo "Or manually:"
    echo "  source venv/bin/activate && python download_rlog_files.py && deactivate"
else
    echo "You can now run: $PYTHON_CMD download_rlog_files.py"
fi
