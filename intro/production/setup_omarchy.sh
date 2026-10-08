#!/usr/bin/env bash
# Set up the CHRONICA intro production pipeline on an Omarchy / Arch Linux machine with an NVIDIA GPU.
# Run from anywhere:  bash intro/production/setup_omarchy.sh
set -euo pipefail

PROD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$PROD/../.." && pwd)"
echo "production dir: $PROD"
echo "repo:           $REPO"

# 1. GPU check -------------------------------------------------------------
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
else
  echo "WARNING: nvidia-smi not found. Install the NVIDIA driver first (for example: sudo pacman -S nvidia-open-dkms nvidia-utils), reboot, then re-run."
fi

# 2. System packages ----------------------------------------------------------
sudo pacman -S --needed --noconfirm python python-pip ffmpeg nodejs npm rsync wget xz

# 3. Blender 4.1.1 (last release with legacy Eevee; the scene scripts were written for 4.0 legacy Eevee).
#    The official build ships CUDA/OptiX for Cycles and renders Eevee on the GPU directly (no xvfb needed).
BL_DIR="$HOME/.local/opt/blender-4.1.1-linux-x64"
if [ ! -x "$BL_DIR/blender" ]; then
  mkdir -p "$HOME/.local/opt"
  wget -q --show-progress -O /tmp/blender-4.1.1.tar.xz https://download.blender.org/release/Blender4.1/blender-4.1.1-linux-x64.tar.xz
  tar -xf /tmp/blender-4.1.1.tar.xz -C "$HOME/.local/opt"
fi
mkdir -p "$HOME/.local/bin"; ln -sfn "$BL_DIR/blender" "$HOME/.local/bin/blender"
"$BL_DIR/blender" -b --version | head -1

# 4. Python venv for the 2.5D embroidery library (numpy, numba, OpenCV, SciPy, OIDN) ---------
python -m venv "$PROD/.venv"
"$PROD/.venv/bin/pip" install -q --upgrade pip
"$PROD/.venv/bin/pip" install -q numpy scipy numba opencv-python-headless pillow openexr pyoidn librosa
# Blender's own Python also needs numpy/cv2 for some scene scripts:
BPY="$(ls -d "$BL_DIR"/4.1/python/bin/python3* | head -1)"
"$BPY" -m ensurepip -q || true
"$BPY" -m pip install -q numpy opencv-python-headless pillow scipy || true

# 5. Path compatibility ----------------------------------------------------------
# The scripts were written in a cloud container and use absolute paths rooted at the scratchpad below.
# Recreate that root as a symlink to this production folder (and the repo path the game scripts use).
SCRATCH=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd
sudo mkdir -p "$SCRATCH" && sudo chown "$USER" "$SCRATCH" /tmp/claude-0 /tmp/claude-0/-home-user-chronica-ipad
ln -sfn "$PROD" "$SCRATCH/scratchpad"
if [ ! -e /home/user/chronica-ipad ]; then
  sudo mkdir -p /home/user && sudo ln -sfn "$REPO" /home/user/chronica-ipad
fi
echo "NOTE: /tmp is cleared on reboot on Arch; re-run step 5 (or this script) after a reboot."

# 6. Remotion test project (uses your system Chromium/Chrome via --browser-executable if its own download fails)
if [ -f "$PROD/aaa/tools/remotion-test/package.json" ]; then
  (cd "$PROD/aaa/tools/remotion-test" && npm install --silent)
fi

echo
echo "Setup done. Activate the venv with:  source $PROD/.venv/bin/activate"
echo "Then open Claude Code in the repo:   cd $REPO && claude remote-control"
echo "and ask it to read intro/production/HANDOFF.md and continue."
