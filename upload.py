#!/usr/bin/env python3
"""
RClone Google Drive Upload Script for rlogs
==========================================

This script uploads rlog files from the local rlogs directory to Google Drive using rclone.
It maintains folder structure and keeps each device folder under 2GB by creating numbered subfolders.

Prerequisites:
1. Install rclone:
   - Download from https://rclone.org/downloads/
   - Or use: winget install Rclone.Rclone (Windows)
   - Or use: choco install rclone (Windows with Chocolatey)

2. Configure rclone for Google Drive:
   rclone config
   - Choose "n" for new remote
   - Name it "gdrive" (or change REMOTE_NAME below)
   - Choose "drive" for Google Drive
   - Follow the authentication prompts

Features:
- Uses rclone for fast, reliable uploads
- Maintains folder structure (device/dongle_id/)
- Keeps each device folder under 2GB by creating numbered subfolders
- Skips files that already exist on Google Drive
- Shows progress and transfer speeds
- Handles large files efficiently
- Supports resumable transfers

Usage:
    python upload_to_google_drive_rclone.py
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time

# Configuration
REMOTE_NAME = "gdrive"  # Name of your rclone remote (change if different)
GOOGLE_DRIVE_FOLDER = "rlogs"  # Main folder name in Google Drive
MAX_FOLDER_SIZE_GB = 1.9  # Maximum size per device folder in GB
MAX_FOLDER_SIZE_BYTES = int(MAX_FOLDER_SIZE_GB * 1024 * 1024 * 1024)

# Get directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RLOGS_DIR = os.path.join(SCRIPT_DIR, "rlogs")

class RCloneUploader:
    def __init__(self):
        self.remote_path = f"{REMOTE_NAME}:{GOOGLE_DRIVE_FOLDER}"
        
    def check_rclone_installed(self) -> bool:
        """Check if rclone is installed and accessible."""
        try:
            result = subprocess.run(["rclone", "version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"Found rclone: {version_line}")
                return True
            else:
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def check_remote_configured(self) -> bool:
        """Check if the Google Drive remote is configured."""
        try:
            result = subprocess.run(["rclone", "listremotes"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                remotes = result.stdout.strip().split('\n')
                remote_with_colon = f"{REMOTE_NAME}:"
                if remote_with_colon in remotes:
                    print(f"Found configured remote: {REMOTE_NAME}")
                    return True
                else:
                    print(f"Available remotes: {', '.join(remotes)}")
                    return False
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_remote_folder_size(self, remote_folder: str) -> int:
        """Get the size of a remote folder in bytes."""
        try:
            result = subprocess.run([
                "rclone", "size", f"{self.remote_path}/{remote_folder}", "--json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                size_info = json.loads(result.stdout)
                return size_info.get('bytes', 0)
            else:
                # Folder might not exist yet
                return 0
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return 0
    
    def get_local_folder_size(self, folder_path: Path) -> int:
        """Get the size of a local folder in bytes."""
        total_size = 0
        for file_path in folder_path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def list_remote_files(self, remote_folder: str) -> set:
        """List all files in a remote folder."""
        try:
            result = subprocess.run([
                "rclone", "lsf", f"{self.remote_path}/{remote_folder}", "--recursive"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                files = set(line.strip() for line in result.stdout.strip().split('\n') if line.strip())
                return files
            else:
                return set()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return set()
    
    def find_best_subfolder(self, device_name: str, dongle_id: str, file_size: int) -> str:
        """Find the best subfolder for a file, considering size limits."""
        base_folder = f"{device_name}/{dongle_id}"
        
        # Try subfolders starting from 1
        subfolder_num = 1
        while True:
            if subfolder_num == 1:
                # Try the main folder first
                current_folder = base_folder
            else:
                # Try numbered subfolders
                current_folder = f"{base_folder}_part{subfolder_num}"
            
            current_size = self.get_remote_folder_size(current_folder)
            
            # Check if file would fit in this folder
            if current_size + file_size <= MAX_FOLDER_SIZE_BYTES:
                return current_folder
            
            subfolder_num += 1
            
            # Safety check to avoid infinite loop
            if subfolder_num > 100:
                print(f"Warning: Too many subfolders for {base_folder}, using part{subfolder_num}")
                return f"{base_folder}_part{subfolder_num}"
    
    def group_files_by_size_limit(self, device_folder: Path) -> List[Tuple[str, List[Path]]]:
        """Group files into subfolders based on size limits."""
        files = []
        for file_path in device_folder.rglob('*'):
            if file_path.is_file() and any(ext in file_path.name.lower() 
                                         for ext in ['.rlog', '.bz2', '.gz', '.zst']):
                files.append(file_path)
        
        # Sort files by name for consistent grouping
        files.sort(key=lambda x: x.name)
        
        groups = []
        current_group = []
        current_size = 0
        group_num = 1
        
        device_name = device_folder.parent.name
        dongle_id = device_folder.name
        
        for file_path in files:
            file_size = file_path.stat().st_size
            
            # If adding this file would exceed the limit, start a new group
            if current_size + file_size > MAX_FOLDER_SIZE_BYTES and current_group:
                if group_num == 1:
                    folder_name = f"{device_name}/{dongle_id}"
                else:
                    folder_name = f"{device_name}/{dongle_id}_part{group_num}"
                
                groups.append((folder_name, current_group))
                current_group = []
                current_size = 0
                group_num += 1
            
            current_group.append(file_path)
            current_size += file_size
        
        # Add the last group if it has files
        if current_group:
            if group_num == 1:
                folder_name = f"{device_name}/{dongle_id}"
            else:
                folder_name = f"{device_name}/{dongle_id}_part{group_num}"
            groups.append((folder_name, current_group))
        
        return groups
    
    def upload_files(self, files: List[Path], remote_folder: str) -> Dict[str, int]:
        """Upload a list of files to a specific remote folder."""
        stats = {'uploaded': 0, 'skipped': 0, 'failed': 0}
        
        if not files:
            return stats
        
        print(f"\nUploading to: {remote_folder}")
        print(f"Files to upload: {len(files)}")
        
        # Get list of existing files in remote folder
        existing_files = self.list_remote_files(remote_folder)
        
        # Filter out files that already exist
        files_to_upload = []
        for file_path in files:
            if file_path.name in existing_files:
                print(f"  ⏭️  Skipping existing file: {file_path.name}")
                stats['skipped'] += 1
            else:
                files_to_upload.append(file_path)
        
        if not files_to_upload:
            print("  ✅ All files already exist, nothing to upload")
            return stats
        
        # Create a temporary directory with the files to upload
        temp_dir = Path(SCRIPT_DIR) / "temp_upload"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Copy files to temp directory
            for file_path in files_to_upload:
                temp_file = temp_dir / file_path.name
                shutil.copy2(file_path, temp_file)
            
            # Upload using rclone
            remote_dest = f"{self.remote_path}/{remote_folder}"
            
            cmd = [
                "rclone", "copy",
                str(temp_dir),
                remote_dest,
                "--progress",
                "--transfers", "16",  # Parallel transfers
                "--checkers", "16",   # Parallel file checks
                "--tpslimit", "100",   # Transfers per second limit
                "--retries", "3",    # Retry failed transfers
                "--low-level-retries", "10",
                "--stats", "30s",    # Stats every 30 seconds
                "--stats-one-line"   # Compact stats
            ]
            
            print(f"  📤 Starting upload of {len(files_to_upload)} files...")
            
            result = subprocess.run(cmd, capture_output=False, text=True)
            
            if result.returncode == 0:
                stats['uploaded'] = len(files_to_upload)
                print(f"  ✅ Successfully uploaded {len(files_to_upload)} files")
            else:
                stats['failed'] = len(files_to_upload)
                print(f"  ❌ Upload failed for {len(files_to_upload)} files")
        
        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
        return stats
    
    def upload_device_folder(self, device_folder: Path) -> Dict[str, int]:
        """Upload all files from a device folder, splitting into subfolders as needed."""
        total_stats = {'uploaded': 0, 'skipped': 0, 'failed': 0}
        
        print(f"\nProcessing device folder: {device_folder}")
        
        # Group files by size limit
        file_groups = self.group_files_by_size_limit(device_folder)
        
        if not file_groups:
            print("  No rlog files found")
            return total_stats
        
        print(f"  Split into {len(file_groups)} folder(s) due to size limits")
        
        for remote_folder, files in file_groups:
            folder_size = sum(f.stat().st_size for f in files)
            print(f"  📁 Folder: {remote_folder} ({folder_size / (1024*1024*1024):.2f} GB)")
            
            stats = self.upload_files(files, remote_folder)
            for key in total_stats:
                total_stats[key] += stats[key]
        
        return total_stats
    
    def upload_all(self) -> Dict[str, int]:
        """Upload all rlog files from the rlogs directory."""
        total_stats = {'uploaded': 0, 'skipped': 0, 'failed': 0}
        
        rlogs_path = Path(RLOGS_DIR)
        if not rlogs_path.exists():
            print(f"Error: rlogs directory not found: {RLOGS_DIR}")
            return total_stats
        
        # Process each device folder
        device_folders = [d for d in rlogs_path.iterdir() if d.is_dir()]
        
        if not device_folders:
            print("No device folders found in rlogs directory")
            return total_stats
        
        print(f"Found {len(device_folders)} device folder(s)")
        
        for device_folder in device_folders:
            # Process each dongle_id folder within the device
            dongle_folders = [d for d in device_folder.iterdir() if d.is_dir()]
            
            for dongle_folder in dongle_folders:
                stats = self.upload_device_folder(dongle_folder)
                for key in total_stats:
                    total_stats[key] += stats[key]
        
        return total_stats

def main():
    print("Upload rlogs to Google Drive")
    print("=" * 40)
    
    uploader = RCloneUploader()
    
    # Check if rclone is installed
    if not uploader.check_rclone_installed():
        print("❌ rclone is not installed or not found in PATH")
        print("\nInstallation options:")
        print("1. Download from: https://rclone.org/downloads/")
        print("2. Windows (winget): winget install Rclone.Rclone")
        print("3. Windows (chocolatey): choco install rclone")
        print("4. Add rclone to your system PATH")
        return
    
    # Check if Google Drive remote is configured
    if not uploader.check_remote_configured():
        print(f"❌ Google Drive remote '{REMOTE_NAME}' is not configured")
        print("\nTo configure rclone for Google Drive:")
        print("1. Run: rclone config")
        print("2. Choose 'n' for new remote")
        print(f"3. Name it '{REMOTE_NAME}'")
        print("4. Choose 'drive' for Google Drive")
        print("5. Follow the authentication prompts")
        return
    
    print(f"📁 Local directory: {RLOGS_DIR}")
    print(f"☁️ Remote destination: {uploader.remote_path}")
    print(f"📏 Max folder size: {MAX_FOLDER_SIZE_GB} GB")
    
    # Start upload
    start_time = time.time()
    stats = uploader.upload_all()
    elapsed_time = time.time() - start_time
    
    # Print summary
    print("\n" + "=" * 40)
    print("Upload Summary:")
    print(f"  Files uploaded: {stats['uploaded']}")
    print(f"  Files skipped (already exist): {stats['skipped']}")
    print(f"  Files failed: {stats['failed']}")
    print(f"  Time elapsed: {elapsed_time / 60:.1f} minutes")
    
    if stats['failed'] > 0:
        print(f"\n⚠️  {stats['failed']} files failed to upload")
        print("Check your internet connection and rclone configuration")
    elif stats['uploaded'] > 0:
        print("\n✅ All files uploaded successfully!")
    else:
        print("\n✅ All files already exist on Google Drive!")

if __name__ == "__main__":
    main()
