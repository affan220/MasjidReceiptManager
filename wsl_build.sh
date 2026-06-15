#!/usr/bin/env bash
# WSL helper to prepare environment and run Buildozer for Android
set -e

echo "This script will install system packages (via apt), create a venv, install buildozer, and run the Android build."
read -p "Proceed? [y/N] " yn
if [[ "$yn" != "y" && "$yn" != "Y" ]]; then
  echo "Aborted."
  exit 1
fi

# Update and install system deps
sudo apt update
sudo apt install -y python3-pip python3-venv git openjdk-17-jdk zip unzip build-essential libssl-dev libffi-dev

# Create and activate venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install buildozer and cython
pip install buildozer
pip install cython==0.29.33

# Move to project dir (assumes script is in project root)
PROJECT_DIR=$(pwd)
echo "Project directory: $PROJECT_DIR"

# Verify buildozer.spec
if [ ! -f buildozer.spec ]; then
  echo "No buildozer.spec found. Run 'buildozer init' to create one, or place this script in the project root." 
  exit 1
fi

# Run build (this will download Android SDK/NDK on first run)
# This step may take a long time on first invocation.
buildozer -v android debug

echo "Build finished. APK should be in the bin/ directory."
