# source this file: environment for the CHRONICA intro toolchain (all paths isolated under aaa/tools; nothing installed system-wide)
T=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools
export PATH=/opt/node22/bin:$PATH
# Remotion: Playwright's headless shell (Remotion's own download from remotion.media is blocked by the proxy)
export REMOTION_BROWSER=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell
# bpy 5.2.2 LTS (Python 3.13 venv, sees system numpy/cv2/PIL): Eevee headless via locally-extracted Mesa EGL (no xvfb needed)
export BPY_PY=$T/bpy313/bin/python
bpy_env() { LD_LIBRARY_PATH=$T/egl/root/usr/lib/x86_64-linux-gnu __EGL_VENDOR_LIBRARY_FILENAMES=$T/egl/root/usr/share/glvnd/egl_vendor.d/50_mesa.json "$@"; }
# pyoidn (OIDN 2.5 CPU) + OpenEXR bindings for python3.13
export PYOIDN_PATH=$T/pylib            # use: PYTHONPATH=$PYOIDN_PATH python3 ...
# Real-ESRGAN (ncnn) on lavapipe CPU Vulkan, Python 3.12 only
esrgan_env() { LD_LIBRARY_PATH=$T/vk/root/usr/lib/x86_64-linux-gnu:$T/vk/root/usr/lib/llvm-18/lib VK_ICD_FILENAMES=$T/vk/lvp_icd_local.json PYTHONPATH=$T/py312 "$@"; }
# Blender 4.0.2 (apt) Eevee legacy needs a virtual X display:
#   xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P script.py -- args
