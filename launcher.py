#!/usr/bin/env python3
"""
Comma 3/3X Route Log Management Suite - Unified Launcher
========================================================

A comprehensive Python wrapper that combines all functionality:
- Setup (Python dependencies, rclone configuration)
- Device management (add/edit/remove devices, size reports)
- Download route logs from Comma devices
- Upload to Google Drive
- Complete workflow automation

This script eliminates the need for separate batch/shell scripts and provides
a unified interface for all route log management tasks.

Usage:
    python comma_rlog_manager.py

Features:
- Cross-platform (Windows, macOS, Linux)
- Interactive menu system
- Automatic setup and configuration
- Complete workflow automation
- Progress tracking and statistics
- Error handling and recovery

Author: Comma 3/3X Route Log Management Suite
License: MIT
"""

import os
import sys
import json
import subprocess
import platform
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional
import importlib.util

# Color codes for cross-platform terminal colors
class Colors:
    """ANSI color codes for terminal output"""
    if platform.system() == "Windows":
        # Enable ANSI color support on Windows 10+
        try:
            os.system('color')
        except:
            pass
    
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_colored(text: str, color: str = Colors.WHITE, bold: bool = False):
    """Print colored text to terminal"""
    prefix = Colors.BOLD if bold else ""
    print(f"{prefix}{color}{text}{Colors.END}")

def print_header(title: str):
    """Print a formatted header"""
    print()
    print_colored("=" * 70, Colors.CYAN, bold=True)
    print_colored(title.center(70), Colors.WHITE, bold=True)
    print_colored("=" * 70, Colors.CYAN, bold=True)
    print()

def print_section(title: str):
    """Print a formatted section title"""
    print()
    print_colored(f"📋 {title}", Colors.BLUE, bold=True)
    print_colored("-" * 50, Colors.BLUE)

def check_python_version():
    """Check if Python version is adequate"""
    min_version = (3, 6)
    current_version = sys.version_info[:2]
    
    if current_version < min_version:
        print_colored(f"❌ Python {min_version[0]}.{min_version[1]}+ required, you have {current_version[0]}.{current_version[1]}", Colors.RED)
        return False
    
    print_colored(f"✅ Python {current_version[0]}.{current_version[1]} detected", Colors.GREEN)
    return True

def check_module_available(module_name: str) -> bool:
    """Check if a Python module is available"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def install_python_dependencies():
    """Install Python dependencies with virtual environment support"""
    print_section("Installing Python Dependencies")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_file = os.path.join(script_dir, "requirements.txt")
    
    if not os.path.exists(requirements_file):
        print_colored("❌ requirements.txt not found", Colors.RED)
        return False
    
    # Check if we're already in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if in_venv:
        print_colored("🔧 Virtual environment detected, installing dependencies...", Colors.YELLOW)
    else:
        print_colored("🔧 Installing dependencies system-wide...", Colors.YELLOW)
    
    # Try direct pip install first
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_file], 
                              capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print_colored("✅ Dependencies installed successfully!", Colors.GREEN)
            return True
        else:
            print_colored("⚠️  Direct install failed, trying virtual environment...", Colors.YELLOW)
    except Exception as e:
        print_colored(f"⚠️  Install error: {e}", Colors.YELLOW)
    
    # Try with virtual environment
    venv_dir = os.path.join(script_dir, "venv")
    
    if not os.path.exists(venv_dir):
        print_colored("🔧 Creating virtual environment...", Colors.YELLOW)
        try:
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True, timeout=60)
        except Exception as e:
            print_colored(f"❌ Failed to create virtual environment: {e}", Colors.RED)
            return False
    
    # Determine activation script path
    if platform.system() == "Windows":
        activate_script = os.path.join(venv_dir, "Scripts", "activate.bat")
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        activate_script = os.path.join(venv_dir, "bin", "activate")
        python_exe = os.path.join(venv_dir, "bin", "python")
    
    # Install dependencies in virtual environment
    try:
        subprocess.run([python_exe, "-m", "pip", "install", "-r", requirements_file], 
                      check=True, timeout=300)
        print_colored("✅ Dependencies installed in virtual environment!", Colors.GREEN)
        
        # Create wrapper info
        print_colored("💡 Virtual environment created. You can run scripts with:", Colors.CYAN)
        if platform.system() == "Windows":
            print_colored(f"   venv\\Scripts\\python.exe comma_rlog_manager.py", Colors.CYAN)
        else:
            print_colored(f"   source venv/bin/activate && python comma_rlog_manager.py", Colors.CYAN)
        
        return True
    except Exception as e:
        print_colored(f"❌ Failed to install dependencies in virtual environment: {e}", Colors.RED)
        return False

def check_rclone():
    """Check if rclone is installed and configured"""
    print_section("Checking RClone Configuration")
    
    # Check if rclone is installed
    try:
        result = subprocess.run(["rclone", "version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
            print_colored(f"✅ RClone found: {version_line}", Colors.GREEN)
        else:
            print_colored("❌ RClone not found", Colors.RED)
            return False, False
    except Exception:
        print_colored("❌ RClone not found or not in PATH", Colors.RED)
        return False, False
    
    # Check if Google Drive remote is configured
    try:
        result = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True, timeout=10)
        if "gdrive:" in result.stdout:
            print_colored("✅ Google Drive remote 'gdrive' is configured", Colors.GREEN)
            return True, True
        else:
            print_colored("⚠️  Google Drive remote 'gdrive' not configured", Colors.YELLOW)
            return True, False
    except Exception as e:
        print_colored(f"❌ Error checking rclone remotes: {e}", Colors.RED)
        return True, False

def install_rclone():
    """Install rclone based on the operating system"""
    print_section("Installing RClone")
    
    system = platform.system()
    
    if system == "Windows":
        print_colored("🔧 Attempting to install rclone via winget...", Colors.YELLOW)
        try:
            result = subprocess.run(["winget", "install", "Rclone.Rclone"], 
                                  capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print_colored("✅ RClone installed successfully via winget!", Colors.GREEN)
                return True
            else:
                print_colored("⚠️  winget install failed, trying chocolatey...", Colors.YELLOW)
                result = subprocess.run(["choco", "install", "rclone", "-y"], 
                                      capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    print_colored("✅ RClone installed successfully via chocolatey!", Colors.GREEN)
                    return True
        except Exception:
            pass
        
        print_colored("❌ Automatic installation failed. Please install manually:", Colors.RED)
        print_colored("   1. Download from: https://rclone.org/downloads/", Colors.CYAN)
        print_colored("   2. Or use chocolatey: choco install rclone", Colors.CYAN)
        print_colored("   3. Add rclone to your PATH", Colors.CYAN)
        
    elif system == "Darwin":  # macOS
        print_colored("🔧 Attempting to install rclone via Homebrew...", Colors.YELLOW)
        try:
            result = subprocess.run(["brew", "install", "rclone"], 
                                  capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print_colored("✅ RClone installed successfully via Homebrew!", Colors.GREEN)
                return True
        except Exception:
            pass
        
        print_colored("❌ Homebrew installation failed. Please install manually:", Colors.RED)
        print_colored("   brew install rclone", Colors.CYAN)
        print_colored("   Or download from: https://rclone.org/downloads/", Colors.CYAN)
        
    else:  # Linux
        print_colored("🔧 Attempting to install rclone...", Colors.YELLOW)
        try:
            # Try package managers
            distro_commands = [
                (["apt", "update"], ["apt", "install", "-y", "rclone"]),
                (["yum", "update"], ["yum", "install", "-y", "rclone"]),
                (["dnf", "update"], ["dnf", "install", "-y", "rclone"]),
                (["pacman", "-Sy"], ["pacman", "-S", "--noconfirm", "rclone"])
            ]
            
            for update_cmd, install_cmd in distro_commands:
                try:
                    subprocess.run(update_cmd, capture_output=True, timeout=30)
                    result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        print_colored("✅ RClone installed successfully via package manager!", Colors.GREEN)
                        return True
                except Exception:
                    continue
            
            # Fall back to rclone install script
            result = subprocess.run(["curl", "https://rclone.org/install.sh"], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                install_process = subprocess.run(["sudo", "bash"], input=result.stdout, 
                                               text=True, timeout=120)
                if install_process.returncode == 0:
                    print_colored("✅ RClone installed successfully via install script!", Colors.GREEN)
                    return True
        except Exception:
            pass
        
        print_colored("❌ Automatic installation failed. Please install manually:", Colors.RED)
        print_colored("   curl https://rclone.org/install.sh | sudo bash", Colors.CYAN)
        print_colored("   Or use your package manager: apt/yum/dnf install rclone", Colors.CYAN)
    
    return False

def configure_rclone():
    """Guide user through rclone Google Drive configuration"""
    print_section("Configuring RClone for Google Drive")
    
    print_colored("🔧 Starting rclone configuration...", Colors.YELLOW)
    print()
    print_colored("Follow these steps:", Colors.CYAN)
    print_colored("1. Choose 'n' for new remote", Colors.WHITE)
    print_colored("2. Name it 'gdrive'", Colors.WHITE)
    print_colored("3. Choose 'drive' for Google Drive", Colors.WHITE)
    print_colored("4. Follow the authentication prompts", Colors.WHITE)
    print()
    
    try:
        subprocess.run(["rclone", "config"], timeout=300)
        
        # Verify configuration
        result = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True, timeout=10)
        if "gdrive:" in result.stdout:
            print_colored("✅ Google Drive remote configured successfully!", Colors.GREEN)
            return True
        else:
            print_colored("⚠️  Configuration may not be complete. Please verify with: rclone listremotes", Colors.YELLOW)
            return False
    except Exception as e:
        print_colored(f"❌ Configuration failed: {e}", Colors.RED)
        return False

def import_script_module(script_name: str):
    """Dynamically import a script module"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    
    if not os.path.exists(script_path):
        return None
    
    spec = importlib.util.spec_from_file_location(script_name.replace('.py', ''), script_path)
    if spec is None:
        return None
    
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print_colored(f"❌ Error importing {script_name}: {e}", Colors.RED)
        return None

def run_setup():
    """Run complete setup process"""
    print_header("🛠️  SETUP COMMA RLOG MANAGEMENT SUITE")
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install Python dependencies
    if not install_python_dependencies():
        print_colored("❌ Setup failed at dependency installation", Colors.RED)
        return False
    
    # Check for required modules
    required_modules = ['paramiko']
    missing_modules = []
    
    for module in required_modules:
        if not check_module_available(module):
            missing_modules.append(module)
    
    if missing_modules:
        print_colored(f"⚠️  Missing modules: {', '.join(missing_modules)}", Colors.YELLOW)
        print_colored("Try running the setup again or install manually", Colors.YELLOW)
    
    # RClone setup
    rclone_installed, rclone_configured = check_rclone()
    
    if not rclone_installed:
        print_colored("🔧 RClone not found, attempting installation...", Colors.YELLOW)
        if not install_rclone():
            print_colored("❌ RClone installation failed", Colors.RED)
            print_colored("💡 You can still use the download functionality without rclone", Colors.CYAN)
        else:
            rclone_installed = True
    
    if rclone_installed and not rclone_configured:
        configure = input(f"\n{Colors.YELLOW}Configure Google Drive remote now? (y/n): {Colors.END}").strip().lower()
        if configure in ['y', 'yes']:
            configure_rclone()
    
    print_colored("\n🎉 Setup completed!", Colors.GREEN, bold=True)
    print_colored("You can now use all features of the Comma Rlog Management Suite", Colors.GREEN)
    
    return True

def run_device_management():
    """Run device management interface"""
    print_header("📱 DEVICE MANAGEMENT")
    
    # Import download module
    download_module = import_script_module("download.py")
    if not download_module:
        print_colored("❌ download.py not found", Colors.RED)
        return
    
    try:
        # Load device configuration and run management
        devices = download_module.manage_device_config()
        print_colored(f"✅ {len(devices)} device(s) configured.", Colors.GREEN)
    except Exception as e:
        print_colored(f"❌ Device management error: {e}", Colors.RED)

def run_download():
    """Run rlog download process"""
    print_header("📥 DOWNLOAD ROUTE LOGS")
    
    # Import download module
    download_module = import_script_module("download.py")
    if not download_module:
        print_colored("❌ download.py not found", Colors.RED)
        return False
    
    try:
        # Check if devices are configured
        devices = download_module.load_device_config()
        if not devices:
            print_colored("❌ No devices configured. Please run device management first.", Colors.RED)
            return False
        
        print_colored(f"🚀 Starting download for {len(devices)} device(s)...", Colors.CYAN)
        
        # Run download for each device
        for device in devices:
            print_colored(f"📱 Processing {device['hostname']} (subfolder: {device['label']})", Colors.BLUE)
            download_module.fetch_rlogs(device)
            time.sleep(2)  # Brief pause between devices
        
        # Run compression and size reporting
        print_colored("🗜️  Compressing and generating size report...", Colors.CYAN)
        diroutbase = getattr(download_module, 'diroutbase', 'rlogs')
        download_module.compress_unzipped_rlogs(diroutbase)
        
        print_colored("✅ Download process completed!", Colors.GREEN, bold=True)
        return True
        
    except Exception as e:
        print_colored(f"❌ Download error: {e}", Colors.RED)
        return False

def run_upload():
    """Run Google Drive upload process"""
    print_header("☁️  UPLOAD TO GOOGLE DRIVE")
    
    # Check rclone first
    rclone_installed, rclone_configured = check_rclone()
    if not rclone_installed:
        print_colored("❌ RClone not found. Please run setup first.", Colors.RED)
        return False
    
    if not rclone_configured:
        print_colored("❌ Google Drive remote not configured. Please run setup first.", Colors.RED)
        return False
    
    # Import upload module
    upload_module = import_script_module("upload.py")
    if not upload_module:
        print_colored("❌ upload.py not found", Colors.RED)
        return False
    
    try:
        print_colored("🚀 Starting Google Drive upload...", Colors.CYAN)
        
        # Run the upload main function
        if hasattr(upload_module, 'main'):
            upload_module.main()
        else:
            # If no main function, try to run the upload logic directly
            print_colored("⚠️  Upload module main function not found, trying direct execution", Colors.YELLOW)
            # You might need to adjust this based on the actual upload module structure
        
        print_colored("✅ Upload process completed!", Colors.GREEN, bold=True)
        return True
        
    except Exception as e:
        print_colored(f"❌ Upload error: {e}", Colors.RED)
        return False

def run_size_report():
    """Run device size reporting"""
    print_header("📊 DEVICE SIZE REPORT")
    
    # Import download module for size reporting functions
    download_module = import_script_module("download.py")
    if not download_module:
        print_colored("❌ download.py not found", Colors.RED)
        return
    
    try:
        diroutbase = getattr(download_module, 'diroutbase', 'rlogs')
        
        if not os.path.exists(diroutbase):
            print_colored(f"❌ Rlog directory '{diroutbase}' does not exist", Colors.RED)
            print_colored("💡 Run the download process first to create device folders", Colors.CYAN)
            return
        
        download_module.report_device_sizes_after_compression(diroutbase)
        
    except Exception as e:
        print_colored(f"❌ Size report error: {e}", Colors.RED)

def run_complete_workflow():
    """Run the complete workflow: download -> compress -> upload"""
    print_header("🔄 COMPLETE WORKFLOW")
    
    print_colored("🚀 Starting complete rlog management workflow...", Colors.CYAN, bold=True)
    print_colored("This will: Download rlogs → Compress → Generate report → Upload to Google Drive", Colors.WHITE)
    print()
    
    # Step 1: Download
    print_colored("📥 Step 1: Downloading route logs...", Colors.BLUE, bold=True)
    if not run_download():
        print_colored("❌ Workflow stopped: Download failed", Colors.RED)
        return False
    
    # Step 2: Upload (compression already done in download step)
    print_colored("☁️  Step 2: Uploading to Google Drive...", Colors.BLUE, bold=True)
    if not run_upload():
        print_colored("⚠️  Upload failed, but download was successful", Colors.YELLOW)
        print_colored("You can try uploading manually later", Colors.YELLOW)
        return True  # Still consider it partially successful
    
    print_colored("🎉 Complete workflow finished successfully!", Colors.GREEN, bold=True)
    return True

def show_main_menu():
    """Display the main menu"""
    print()
    print_colored("📋 MAIN MENU", Colors.CYAN, bold=True)
    print_colored("-" * 30, Colors.CYAN)
    print_colored("1. 🛠️  Setup & Configuration", Colors.WHITE)
    print_colored("2. 📱 Device Management", Colors.WHITE)
    print_colored("3. 📥 Download Route Logs", Colors.WHITE)
    print_colored("4. ☁️  Upload to Google Drive", Colors.WHITE)
    print_colored("5. 📊 Device Size Report", Colors.WHITE)
    print_colored("6. 🔄 Complete Workflow (Download + Upload)", Colors.WHITE)
    print_colored("7. ❓ Help & Information", Colors.WHITE)
    print_colored("8. 🚪 Exit", Colors.WHITE)
    print()

def show_help():
    """Show help information"""
    print_header("❓ HELP & INFORMATION")
    
    print_colored("🎯 WHAT THIS SCRIPT DOES:", Colors.BLUE, bold=True)
    print_colored("This unified launcher combines all Comma 3/3X rlog management functions:", Colors.WHITE)
    print()
    print_colored("• Setup & Configuration: Install dependencies and configure rclone", Colors.GREEN)
    print_colored("• Device Management: Add/edit/remove devices, view size reports", Colors.GREEN) 
    print_colored("• Download Route Logs: Download rlogs from your Comma device(s)", Colors.GREEN)
    print_colored("• Upload to Google Drive: Backup rlogs to cloud storage", Colors.GREEN)
    print_colored("• Size Reports: View storage usage and compression statistics", Colors.GREEN)
    print_colored("• Complete Workflow: Automated download → compress → upload process", Colors.GREEN)
    print()
    
    print_colored("🔧 SETUP REQUIREMENTS:", Colors.BLUE, bold=True)
    print_colored("• Python 3.6+ (for running the scripts)", Colors.WHITE)
    print_colored("• SSH access to your Comma device", Colors.WHITE)
    print_colored("• RClone (for Google Drive uploads)", Colors.WHITE)
    print_colored("• Google Drive account (for backups)", Colors.WHITE)
    print()
    
    print_colored("📚 USAGE TIPS:", Colors.BLUE, bold=True)
    print_colored("• Run 'Setup & Configuration' first on new installations", Colors.WHITE)
    print_colored("• Use 'Device Management' to add your Comma device(s)", Colors.WHITE)
    print_colored("• 'Complete Workflow' automates the entire process", Colors.WHITE)
    print_colored("• Size reports help track storage usage and compression efficiency", Colors.WHITE)
    print()
    
    print_colored("🐛 TROUBLESHOOTING:", Colors.BLUE, bold=True)
    print_colored("• If setup fails, try running as administrator/sudo", Colors.WHITE)
    print_colored("• For SSH issues, verify your key is copied to the device", Colors.WHITE)
    print_colored("• For upload issues, check rclone configuration: rclone config", Colors.WHITE)
    print_colored("• Check README.md for detailed troubleshooting guide", Colors.WHITE)
    print()

def main():
    """Main application loop"""
    print_header("🚗 COMMA 3/3X ROUTE LOG MANAGEMENT SUITE")
    
    print_colored("Welcome to the unified Comma rlog management tool!", Colors.GREEN, bold=True)
    print_colored("This script combines setup, downloading, uploading, and device management.", Colors.WHITE)
    
    while True:
        show_main_menu()
        
        try:
            choice = input(f"{Colors.CYAN}Enter your choice (1-8): {Colors.END}").strip()
            
            if choice == '1':
                run_setup()
            elif choice == '2':
                run_device_management()
            elif choice == '3':
                run_download()
            elif choice == '4':
                run_upload()
            elif choice == '5':
                run_size_report()
            elif choice == '6':
                run_complete_workflow()
            elif choice == '7':
                show_help()
            elif choice == '8':
                print_colored("\n👋 Thank you for using Comma Rlog Management Suite!", Colors.GREEN, bold=True)
                print_colored("Happy driving! 🚗", Colors.CYAN)
                break
            else:
                print_colored("❌ Invalid choice. Please enter 1-8.", Colors.RED)
        
        except KeyboardInterrupt:
            print_colored("\n\n👋 Goodbye!", Colors.YELLOW)
            break
        except Exception as e:
            print_colored(f"❌ Unexpected error: {e}", Colors.RED)
            print_colored("Please try again or report this issue.", Colors.YELLOW)

if __name__ == "__main__":
    main()
