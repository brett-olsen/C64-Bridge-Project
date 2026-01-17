
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

#!/usr/bin/env python3
import os
import pty
import select
import socket
import json
import time
import string

# ========= Config via environment (defaults are sane) =========
PI_IP   = os.getenv("C64KBD_PI_IP", "192.168.1.36")
PI_PORT = int(os.getenv("C64KBD_PI_PORT", "9999"))
TOKEN   = os.getenv("C64KBD_TOKEN", "ILoveMyCommodoreC64")

DEVICE_LINK = os.getenv("C64KBD_DEVICE_LINK", "/tmp/c64kbd0")

# 0 = just decode/log, 1 = forward decoded chars to Pi LAN daemon
FORWARD = os.getenv("C64KBD_FORWARD", "1") == "1"
DEBUG   = os.getenv("C64KBD_DEBUG", "1") == "1"

# Optional batching of decoded chars before sending to Pi (milliseconds)
BATCH_MS = int(os.getenv("C64KBD_BATCH_MS", "25"))  # 0 disables batching

# C64/PETSCII safety: uppercase on PC HID implies SHIFT, which yields graphics on C64
FORCE_UNSHIFT_LETTERS = os.getenv("C64KBD_FORCE_UNSHIFT_LETTERS", "1") == "1"

PRINTABLE = set(string.printable)

# ========= Import your existing keymaps =========
# Run from repo root OR ensure PYTHONPATH includes repo root (runner already does).
try:
    from utils.c64_keymaps import rawKeys, defaultMap
except ModuleNotFoundError:
    from c64_keymaps import rawKeys, defaultMap


def send_to_pi_type(text: str) -> None:
    msg = {"token": TOKEN, "op": "type", "text": text}
    data = (json.dumps(msg) + "\n").encode("utf-8")
    with socket.create_connection((PI_IP, PI_PORT), timeout=3) as s:
        s.sendall(data)


def normalize_bits_segment(seg: str) -> str:
    return seg.strip().replace(" ", "")


def build_reverse_maps():
    """
    Builds:
      SEG_TO_KEY:  "0,1,0,0,1,1,1" -> "W" / "Return" / "Space" / etc
      COMBO_TO_CHAR: "LeftShift+1" -> "!" (inverse of defaultMap)
    """
    seg_to_key = {}
    for key_name, bitstr in rawKeys.items():
        seg = ",".join(list(bitstr))
        seg_to_key[seg] = key_name

    combo_to_char = {}
    for k, combo in defaultMap.items():
        try:
            code = int(k)
            ch = chr(code)
        except Exception:
            continue
        if isinstance(combo, str) and combo != "":
            combo_to_char[combo] = ch

    return seg_to_key, combo_to_char


SEG_TO_KEY, COMBO_TO_CHAR = build_reverse_maps()

SPECIAL = {
    "Return": "\n",
    "ENTER": "\n",
    "Space": " ",
    "SPACE": " ",
    "Tab": "\t",
    "TAB": "\t",
    "Backspace": "\b",
    "DEL": "\b",  # treat DEL as backspace for our USB typing use-case
}

MODIFIERS = {"LeftShift", "RightShift", "Shift", "CTRL", "Ctrl", "Commodore", "Alt", "RunStop", "Restore", "Run/Stop"}


def decode_command_line(line: str):
    """
    Input: one serial command line WITHOUT trailing newline.
      - may contain '_' between segments for combos
      - each segment is comma-separated 0/1s (7 digits including restore flag)
    Returns: (keys:list[str], decoded:str|None)
    """
    line = line.strip()
    if not line:
        return ([], None)

    segments = [normalize_bits_segment(s) for s in line.split("_") if s.strip()]
    if not segments:
        return ([], None)

    keys = []
    for seg in segments:
        key = SEG_TO_KEY.get(seg)
        if key is None:
            return ([], None)
        keys.append(key)

    # Single key
    if len(keys) == 1:
        k = keys[0]
        if k in SPECIAL:
            return (keys, SPECIAL[k])
        if len(k) == 1 and k in PRINTABLE:
            return (keys, k)
        if k in COMBO_TO_CHAR:
            return (keys, COMBO_TO_CHAR[k])
        return (keys, None)

    # Combo: try to resolve via inverse defaultMap (e.g. LeftShift+1 -> '!')
    candidates = []

    # as received
    candidates.append("+".join(keys))

    # normalize: modifiers first
    mods = [k for k in keys if k in MODIFIERS]
    rest = [k for k in keys if k not in MODIFIERS]
    if mods and rest:
        candidates.append("+".join(mods + rest))
        candidates.append("+".join(rest + mods))

    # for 2-keys, also swap
    if len(keys) == 2:
        candidates.append(keys[1] + "+" + keys[0])

    for cand in candidates:
        ch = COMBO_TO_CHAR.get(cand)
        if ch is not None:
            return (keys, ch)

    return (keys, None)


def apply_c64_safety(decoded: str) -> str:
    """
    Avoid HID SHIFT for letters when targeting C64-style systems:
    - Sending 'W' typically means SHIFT+w on PC HID, which becomes a graphics symbol on C64.
    - Sending 'w' types the key without SHIFT; C64 often displays uppercase anyway depending on mode.
    """
    if not decoded:
        return decoded
    if FORCE_UNSHIFT_LETTERS and len(decoded) == 1 and decoded.isalpha():
        return decoded.lower()
    return decoded


def main():
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)

    # stable symlink
    try:
        if os.path.islink(DEVICE_LINK) or os.path.exists(DEVICE_LINK):
            os.unlink(DEVICE_LINK)
    except FileNotFoundError:
        pass
    os.symlink(slave_name, DEVICE_LINK)

    print("  ██████╗ ██████╗ ██╗  ██╗      ██████╗ ██████╗ ██╗██████╗  ██████╗ ███████╗    ██████╗ ██████╗  ██████╗      ██╗███████╗ ██████╗████████╗")
    print(" ██╔════╝██╔════╝ ██║  ██║      ██╔══██╗██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝    ██╔══██╗██╔══██╗██╔═══██╗     ██║██╔════╝██╔════╝╚══██╔══╝")
    print(" ██║     ███████╗ ███████║█████╗██████╔╝██████╔╝██║██║  ██║██║  ███╗█████╗█████╗██████╔╝██████╔╝██║   ██║     ██║█████╗  ██║        ██║")
    print(" ██║     ██╔═══██╗╚════██║╚════╝██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝╚════╝██╔═══╝ ██╔══██╗██║   ██║██   ██║██╔══╝  ██║        ██║")
    print(" ╚██████╗╚██████╔╝     ██║      ██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗    ██║     ██║  ██║╚██████╔╝╚█████╔╝███████╗╚██████╗   ██║")
    print("  ╚═════╝ ╚═════╝      ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚════╝ ╚══════╝ ╚═════╝   ╚═╝\n")
    print(" ----------------------------------------------------------------------------------------------------------------------")
    print(" C64-Bridge-Project: A wireless USB Keyboard/HID emulator for the Raspberry Pi Zero 2 W, with a Serial Emulator bridge")
    print(" (can be used with the VibeC64 Project, see https://github.com/bbence84/VibeC64)\n")
    print(" https://github.com/brett-olsen/C64-Bridge-Project/tree/main")
    print(" Version 0.1")
    print(" Created by Brett Olsen - 2026")
    print("----------------------------------------------------------------------------------------------------------------------\n")
    print("Starting C64 keyboard bridge...")
    print(f"Repo root (via runner): {os.getenv('PYTHONPATH','').split(':')[0]}")
    print(f"App should use:   export C64_KEYBOARD_DEVICE_PORT={DEVICE_LINK}")
    print(f"Forward to Pi:    {FORWARD} ({PI_IP}:{PI_PORT})")
    print()
    print("=== C64KBD PTY bridge (decode rawKeys/defaultMap -> Pi HID) ===")
    print(f"PTY slave (real path): {slave_name}")
    print(f"Stable device path   : {DEVICE_LINK}")
    print(f"Forward to Pi        : {FORWARD}")
    print(f"Pi target            : {PI_IP}:{PI_PORT}")
    print(f"Batch ms             : {BATCH_MS}")
    print(f"Force unshift letters: {FORCE_UNSHIFT_LETTERS}")
    print("==============================================================")
    print()

    os.set_blocking(master_fd, False)
    buf = bytearray()

    out_buf = []
    last_flush = time.time()

    while True:
        r, _, _ = select.select([master_fd], [], [], 0.25)
        now = time.time()

        # periodic batch flush
        if FORWARD and BATCH_MS > 0 and out_buf:
            if (now - last_flush) * 1000 >= BATCH_MS:
                try:
                    send_to_pi_type("".join(out_buf))
                except Exception as e:
                    print(f"[WARN] send_to_pi failed: {e!r}")
                out_buf.clear()
                last_flush = now

        if not r:
            continue

        chunk = os.read(master_fd, 4096)
        if not chunk:
            continue
        buf.extend(chunk)

        while b"\n" in buf:
            raw, _, rest = buf.partition(b"\n")
            buf[:] = rest
            line = raw.decode("utf-8", errors="ignore")

            keys, decoded = decode_command_line(line)

            if decoded is None:
                if DEBUG:
                    print(f"[RX] {line.strip()!r} -> (no decode) keys={keys}")
                continue

            decoded = apply_c64_safety(decoded)

            if DEBUG:
                print(f"[RX] {line.strip()!r} -> keys={keys} decoded={decoded!r}")

            if not FORWARD:
                continue

            # Send immediately unless batching enabled
            if BATCH_MS <= 0:
                try:
                    send_to_pi_type(decoded)
                except Exception as e:
                    print(f"[WARN] send_to_pi failed: {e!r}")
            else:
                out_buf.append(decoded)

        time.sleep(0.001)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
