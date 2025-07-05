This script will connect to your Comma 3/3X and download your driving logs to a local directory. The best way is probably rsync but I have no idea how to use that so just wrote this up quicky as an alternative. It should only copy logs that are new/not downloaded yet.

To use it, you'll need to have already connected to your Comma via SSH - There are a lot of instructions available to do that. After that, you can use this script to connect as it'll just reuse your existing SSH key.

There are 2 versions. 
1) download_rlog_files.py - this works on mac and linux but not on Windows
2) download_rlog_files_windows.py - this works on Windows and -should- also work on mac/linux (but I havent tested that)

Step 1 - https://github.com/commaai/openpilot/wiki/SSH#option-1---putty-ssh-client
Step 2 - Download 'Thonny' for your system (Mac/Win/Nix)
Step 3 - Have device connected to wifi / open the script in Thonny and run it 
Step 4 - The files should download to a local directory where you can then upload them somewhere for NNLC training

Good luck!
