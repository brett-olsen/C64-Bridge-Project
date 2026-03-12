
#  ██████╗ ██████╗ ██╗  ██╗      ██████╗ ██████╗ ██╗██████╗  ██████╗ ███████╗    ██████╗ ██████╗  ██████╗      ██╗███████╗ ██████╗████████╗
# ██╔════╝██╔════╝ ██║  ██║      ██╔══██╗██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝    ██╔══██╗██╔══██╗██╔═══██╗     ██║██╔════╝██╔════╝╚══██╔══╝
# ██║     ███████╗ ███████║█████╗██████╔╝██████╔╝██║██║  ██║██║  ███╗█████╗█████╗██████╔╝██████╔╝██║   ██║     ██║█████╗  ██║        ██║
# ██║     ██╔═══██╗╚════██║╚════╝██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝╚════╝██╔═══╝ ██╔══██╗██║   ██║██   ██║██╔══╝  ██║        ██║
# ╚██████╗╚██████╔╝     ██║      ██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗    ██║     ██║  ██║╚██████╔╝╚█████╔╝███████╗╚██████╗   ██║
#  ╚═════╝ ╚═════╝      ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚════╝ ╚══════╝ ╚═════╝   ╚═╝
#
# ----------------------------------------------------------------------------------------------------------------------
# C64-Bridge-Project: A wireless USB Keyboard/HID emulator for the Raspberry Pi Zero 2 W, with a Serial Emulator bridge
# (can be used with the VibeC64 Project, see https://github.com/bbence84/VibeC64)
#
# https://github.com/brett-olsen/C64-Bridge-Project/tree/main
# Version 0.1
# Created by Brett Olsen - 2026
# ----------------------------------------------------------------------------------------------------------------------

#!/usr/bin/env bash
set -euo pipefail

# ---- EDIT THESE IF NEEDED ----
PI_IP="192.168.1.36"
PI_PORT="9999"
TOKEN="ILoveMyCommodoreC64"
# ------------------------------

# Determine repo root (parent of tools/)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

export C64KBD_PI_IP="$PI_IP"
export C64KBD_PI_PORT="$PI_PORT"
export C64KBD_TOKEN="$TOKEN"

export C64KBD_DEVICE_LINK="/tmp/c64kbd0"
export C64KBD_FORWARD="1"
export C64KBD_DEBUG="1"
export C64KBD_BATCH_MS="25"

# Ensure Python can import repo modules like utils.c64_keymaps
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

echo "Starting C64 keyboard bridge..."
echo "Repo root:        ${REPO_ROOT}"
echo "PYTHONPATH:       ${PYTHONPATH}"
echo "App should use:   export C64_KEYBOARD_DEVICE_PORT=/tmp/c64kbd0"
echo "Forwarding to:    ${PI_IP}:${PI_PORT}"
echo

exec python3 "${REPO_ROOT}/tools/c64kbd_bridge.py"
