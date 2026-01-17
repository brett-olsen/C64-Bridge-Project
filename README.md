
<img width="1200" height="640" alt="project-banner" src="https://github.com/user-attachments/assets/d79f426c-7a6e-44c8-abc1-ebfb68187f98" />


# C64-Bridge-Project
A repo for the C64 Bridge Project, a wireless USB Keyboard/HID emulator for the Raspberry Pi Zero 2 W, with a Serial Emulator bridge (can be used with the VibeC64 Project, see https://github.com/bbence84/VibeC64)<br><br>

**What is this Project?**<br>
This project is designed to allow for the remote transmission of keystrokes from a host computer, to the Raspberry Pi Zero 2 W, which then emulates a USB HID keyboard via gadget mode, and relays those keystrokes to the Commodore C64 Ultimate (see https://www.commodore.net/), while this project can have a myriad of uses, it is specifically designed to be a drop-in, zero-code addition to the VibeC64 Project (see https://github.com/bbence84/VibeC64) this then effectively gives VibeC64 the ability to remotely control the physical C64 Ultimate computer, coupled with a webcam, this allows VibeC64 to monitor, control and test basic applications plus games on a physical C64 Ultimate<br><br>
**-- Please consider this project very alpha, it just works barely, and I’ll add more to it and make it more robust when I get time --**<br><br>

**General Requirements**<br>
1 x Computer running some varient of Linux with Python + VibeC64 installed & working locally (I use Arch Linux)<br>
1 X Webcam setup and working with VibeC64 (this will let the AI "see" the C64 Ultimate)<br><br>

**C64 Bridge Hardware**<br>
1 x Pi Zero 2 W<br>
1 x micro-USB data cable<br>
1 x OTG micro-USB shim<br>
1 x micro SD card (at least 4 GB)<br><br>

**C64 Bridge Software**<br>
1 x Raspberry Pi imaging tool<br>
1 x Copy of Raspberry Pi OS Lite (32-bit)<br><br>

****IMPORTANT** on the Raspberry Pi Zero 2 W, the ports are in the following order: POWER - DATA - HDMI**<br>
During the configuration stages, it's totally fine to use the first port, power. When Gadget mode is enabled, and for HID/Keyboard emulation, you need to use the Data Port, this is the middle port, please also take some time to read the connection information below.<br><br>

**NOTE: Be careful with physical connections, typically I used a USB power supply or a USB battery pack to keep the Pi running during configuration, while I am not an electronics engineer, I believe it is best practice to not have multiple cables connected, for example, do not power the Pi Zero and simultaneously connect a data cable to another computer unless you know what you are doing. During setup, 1 cable for power, during testing and during operation 1 cable for data/power seems to work well for this project. If you want to use two cables safely, I believe you need to ensure that the data cable's 5V is disconnected with either a data-only cable, or a 5V blocker. Be careful with your connections and devices! TL;DR only use 1 cable at a time =)**<br><br>

# Getting it up & running<br><br>
**1) Flash the Raspberry Pi OS**<br>
I personally used the Raspberry Pi Imager over at https://github.com/raspberrypi/rpi-imager, however any of the popular Raspberry Pi flashing tools will work (see https://www.raspberrypi.com/software/), for a number of reasons and for increased compatibility I used the following image:<br><br>

- Raspberry Pi OS Lite (32-bit) (see https://www.raspberrypi.com/software/operating-systems/)<br>
When flashing the Pi OS be sure to set the following:<br>
- Device - If asked, choose the correct device, in this case a Raspberry Pi Zero 2 W
- If the flashing app has the option, you may need to choose other OS or choose the image you downloaded, again ensure it is the Pi OS Lite 32-bit
- Hostname: PiZero2W (choose your own, this is what I chose and will be referred to herein)<br>
- Enable: SSH (if asked, I used password authentication)<br>
- Configure Wi-Fi with an SSID/password, set your country<br>
- Set a username/password<br><br>
When the flashing of the Pi OS image has completed, insert the SD card and power on the Pi.<br><br>

**2) Getting the Pi Zero 2 W Running**<br>
Note: First boot of the Pi Zero 2 W may take some time, be patient =)<br><br>
Find the IP address of the Pi Zero from your router, or if mDNS works SSH into your Pi Zero
```
ssh <user>@PiZero2W.local
# or
ssh <user>@<pi-ip>
```
<br>

Update all your packages:<br>
```
sudo apt update
sudo apt -y full-upgrade
sudo reboot
```
(this will take some time, but it’s a good idea to get your packages up to date)<br>
<br>

Configure the Pi Zero, for gadget mode
```
sudo nano /boot/firmware/config.txt
```
<br>

In the [all] section, make the following addition (typically at the end of the file)<br>
```
dtoverlay=dwc2,dr_mode=peripheral
```
<br>

Ensure the required kernel modules load at boot
```
echo -e "dwc2\nlibcomposite" | sudo tee /etc/modules-load.d/usb-gadget.conf >/dev/null
```
<br>

Make the configfs mount persistent, add configfs to /etc/fstab
```
echo "configfs  /sys/kernel/config  configfs  defaults  0  0" | sudo tee -a /etc/fstab >/dev/null
```
<br>

Reboot your Pi Zero
```
sudo reboot
```
<br>

after you have rebooted, verify that the config file changes have stayed persistent, and the UDC exists
```
ls /sys/class/udc
```
expected output should be something like **3f980000.usb**
<br><br><br>

**3) Configure USB gadget mode**<br>
On the Pi Zero, create /usr/local/sbin/gadget-hid-up.sh either manually or using the following script
```
sudo tee /usr/local/sbin/gadget-hid-up.sh >/dev/null <<'SH'
#!/usr/bin/env bash
set -euo pipefail

G=/sys/kernel/config/usb_gadget/g1

mountpoint -q /sys/kernel/config || mount -t configfs none /sys/kernel/config
modprobe libcomposite >/dev/null 2>&1 || true

mkdir -p "$G"
cd "$G"

echo 0x1d6b > idVendor
echo 0x0104 > idProduct

mkdir -p strings/0x409
echo "PiZero2W"            > strings/0x409/serialnumber
echo "PiZero2W Serial+HID" > strings/0x409/product
echo "PiZero2W"            > strings/0x409/manufacturer

mkdir -p configs/c.1/strings/0x409
echo "Config 1: HID Keyboard (+Serial)" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower

# HID keyboard
mkdir -p functions/hid.usb0
echo 1 > functions/hid.usb0/protocol
echo 1 > functions/hid.usb0/subclass
echo 8 > functions/hid.usb0/report_length

# IMPORTANT: write the report descriptor as RAW BYTES (not literal \xNN text)
# Standard boot keyboard descriptor (8-byte reports)
printf '%b' \
'\x05\x01\x09\x06\xa1\x01\x05\x07\x19\xe0\x29\xe7\x15\x00\x25\x01\x75\x01\x95\x08\x81\x02\x95\x01\x75\x08\x81\x01\x95\x05\x75\x01\x05\x08\x19\x01\x29\x05\x91\x02\x95\x01\x75\x03\x91\x01\x95\x06\x75\x08\x15\x00\x25\x65\x05\x07\x19\x00\x29\x65\x81\x00\xc0' \
> functions/hid.usb0/report_desc

ln -sf functions/hid.usb0 configs/c.1/

# Optional ACM serial
mkdir -p functions/acm.usb0
ln -sf functions/acm.usb0 configs/c.1/

# Bind
UDC="$(ls /sys/class/udc | head -n1)"
echo "$UDC" > UDC

echo "UP: bound to UDC=$UDC"
SH

sudo chmod +x /usr/local/sbin/gadget-hid-up.sh
```
<br>

Now create the gadget HID down script, /usr/local/sbin/gadget-hid-down.sh manually or via the following script
```
sudo tee /usr/local/sbin/gadget-hid-down.sh >/dev/null <<'SH'
#!/usr/bin/env bash
set -euo pipefail
G=/sys/kernel/config/usb_gadget/g1
[ -d "$G" ] || exit 0

# Unbind if bound
if [ -f "$G/UDC" ]; then
  echo "" > "$G/UDC" || true
fi

# Remove symlinks first
rm -f "$G/configs/c.1/hid.usb0" 2>/dev/null || true
rm -f "$G/configs/c.1/acm.usb0" 2>/dev/null || true

# Remove functions/config/strings
rm -rf "$G/functions/hid.usb0" "$G/functions/acm.usb0" 2>/dev/null || true
rm -rf "$G/configs/c.1/strings/0x409" "$G/strings/0x409" 2>/dev/null || true
rm -rf "$G/configs/c.1" 2>/dev/null || true

# Remove gadget dir
cd /sys/kernel/config/usb_gadget || exit 0
rmdir g1 2>/dev/null || true
SH

sudo chmod +x /usr/local/sbin/gadget-hid-down.sh
```
<br>

Create a systemd service to bring up the gadget automatically on boot, /etc/systemd/system/usb-gadget-hid.service (again either manually or via the following script)<br>

```
sudo tee /etc/systemd/system/usb-gadget-hid.service >/dev/null <<'UNIT'
[Unit]
Description=USB Gadget (HID Keyboard + optional ACM) for PiZero2W
After=local-fs.target
Wants=local-fs.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/gadget-hid-up.sh
ExecStop=/usr/local/sbin/gadget-hid-down.sh

[Install]
WantedBy=multi-user.target
UNIT
```
<br>

On the Pi Zero, enable and start the service, check for errors as you do this
```
sudo systemctl daemon-reload
sudo systemctl enable --now usb-gadget-hid.service
systemctl status usb-gadget-hid.service --no-pager
```
You should see **active** and **enabled** in green (if your terminal supports colors)
<br><br>

Verify all is working, on the Pi Zero
```
sudo reboot
```
then reconnect and execute:
```
cat /sys/kernel/config/usb_gadget/g1/UDC
```
If all is working, you should see an output similar to **3f980000.usb**, Congrats USB Gadget mode is enabled, that’s the hard part done!<br><br>
<br>

**4) Install the Pi Network Daemon**<br>
First we need to create the Network daemon on the Pi Zero, then we will create a config file, setup a network service so everything runs after boot.<br>

Install the Network Daemon on the Pi Zero 
```
sudo mkdir -p /opt/hid-netd

sudo tee /opt/hid-netd/hid_netd.py >/dev/null <<'PY'

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
# Version 0.1
# Created by Brett Olsen - 2026
# ----------------------------------------------------------------------------------------------------------------------

#!/usr/bin/env python3
import os
import json
import socket
import sys
from typing import Dict, Optional

# --- Config from env (systemd EnvironmentFile sets these) ---
LISTEN = os.getenv("HID_NETD_LISTEN", "0.0.0.0")
PORT   = int(os.getenv("HID_NETD_PORT", "9999"))
TOKEN  = os.getenv("HID_NETD_TOKEN", "ILoveMyCommodoreC64")
HIDDEV = os.getenv("HID_DEVICE", "/dev/hidg0")

# If you use an "armed" gate file, enable it here (optional)
ARM_FILE = os.getenv("HID_NETD_ARM_FILE", "/etc/usb-hid/ARMED")
REQUIRE_ARMED = os.getenv("HID_NETD_REQUIRE_ARMED", "0") == "1"

# --- Minimal HID keymap (US layout) ---
# Modifier bits: 0x02 = Left Shift
MOD_LSHIFT = 0x02

KEYCODES: Dict[str, int] = {
    'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07, 'e': 0x08, 'f': 0x09,
    'g': 0x0A, 'h': 0x0B, 'i': 0x0C, 'j': 0x0D, 'k': 0x0E, 'l': 0x0F,
    'm': 0x10, 'n': 0x11, 'o': 0x12, 'p': 0x13, 'q': 0x14, 'r': 0x15,
    's': 0x16, 't': 0x17, 'u': 0x18, 'v': 0x19, 'w': 0x1A, 'x': 0x1B,
    'y': 0x1C, 'z': 0x1D,

    '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21, '5': 0x22,
    '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26, '0': 0x27,

    ' ': 0x2C,
    '\n': 0x28,  # Enter
    '\t': 0x2B,  # Tab
    '\b': 0x2A,  # Backspace

    '-': 0x2D, '=': 0x2E, '[': 0x2F, ']': 0x30, '\\': 0x31,
    ';': 0x33, "'": 0x34, '`': 0x35, ',': 0x36, '.': 0x37, '/': 0x38,
}

SHIFTED: Dict[str, str] = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=',
    '{': '[', '}': ']',
    '|': '\\',
    ':': ';', '"': "'",
    '~': '`',
    '<': ',', '>': '.', '?': '/',
}

def hid_write_report(fd, mod: int, keycode: int) -> None:
    # 8-byte boot keyboard report: [mod, 0, key1, key2, key3, key4, key5, key6]
    fd.write(bytes([mod, 0, keycode, 0, 0, 0, 0, 0]))
    fd.flush()

def tap_key(fd, mod: int, keycode: int) -> None:
    hid_write_report(fd, mod, keycode)   # press
    hid_write_report(fd, 0, 0)           # release

def char_to_hid(ch: str) -> Optional[tuple]:
    # Returns (modifier, keycode) or None if unsupported
    if ch in KEYCODES:
        return (0, KEYCODES[ch])

    if ch.isalpha():
        # Uppercase -> shift + lowercase key
        if ch.isupper():
            base = ch.lower()
            if base in KEYCODES:
                return (MOD_LSHIFT, KEYCODES[base])
        else:
            if ch in KEYCODES:
                return (0, KEYCODES[ch])
        return None

    if ch in SHIFTED:
        base = SHIFTED[ch]
        if base in KEYCODES:
            return (MOD_LSHIFT, KEYCODES[base])
    return None

def is_armed() -> bool:
    if not REQUIRE_ARMED:
        return True
    return os.path.exists(ARM_FILE)

def handle_message(fd, msg: Dict) -> str:
    if msg.get("token") != TOKEN:
        return "ERR bad token"
    if not is_armed():
        return "ERR not armed"
    op = msg.get("op")
    if op == "type":
        text = msg.get("text", "")
        for ch in text:
            mapped = char_to_hid(ch)
            if mapped is None:
                # ignore unknown characters for now
                continue
            mod, code = mapped
            tap_key(fd, mod, code)
        return "OK"
    return "ERR unknown op"

def main():
    # Open HID device once
    try:
        fd = open(HIDDEV, "wb", buffering=0)
    except Exception as e:
        print(f"[hid-netd] Failed to open {HIDDEV}: {e}", file=sys.stderr)
        sys.exit(1)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((LISTEN, PORT))
        srv.listen(5)
        print(f"[hid-netd] listening on {LISTEN}:{PORT}, HID={HIDDEV}")

        while True:
            conn, addr = srv.accept()
            with conn:
                try:
                    data = b""
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                        while b"\n" in data:
                            line, _, data = data.partition(b"\n")
                            if not line.strip():
                                continue
                            msg = json.loads(line.decode("utf-8", errors="strict"))
                            resp = handle_message(fd, msg)
                            conn.sendall((resp + "\n").encode("utf-8"))
                except Exception as e:
                    # Don't kill the daemon on bad input
                    try:
                        conn.sendall((f"ERR {e}\n").encode("utf-8"))
                    except Exception:
                        pass

if __name__ == "__main__":
    main()
PY

sudo chmod 755 /opt/hid-netd/hid_netd.py
```

Getting things ready to run as a service, on the Pi Zero...
```
sudo mkdir -p /opt/hid-netd
sudo chmod 755 /opt/hid-netd
```
<br>

Create the configuration file for the daemon, this can be tweaked or modified to meet your requirements, or you can just use it "as-is", this is a network service, so do think if this suits your environment. On the Pi Zero, create the config as below either manually or via the below script
```
sudo mkdir -p /etc/hid-netd
sudo tee /etc/hid-netd/config.env >/dev/null <<'ENV'
HID_NETD_LISTEN=0.0.0.0
HID_NETD_PORT=9999
HID_NETD_TOKEN=ILoveMyCommodoreC64
HID_DEVICE=/dev/hidg0
ENV
```
<br>

Once that is done, it’s time to configure the network service, either create the /etc/systemd/system/hid-netd.service file or use the below script
```
sudo tee /etc/systemd/system/hid-netd.service >/dev/null <<'UNIT'
[Unit]
Description=HID Network Daemon (types to /dev/hidg0)
After=network-online.target usb-gadget-hid.service
Wants=network-online.target usb-gadget-hid.service

[Service]
Type=simple
EnvironmentFile=/etc/hid-netd/config.env
WorkingDirectory=/opt/hid-netd
ExecStart=/usr/bin/python3 /opt/hid-netd/hid_netd.py
Restart=on-failure
RestartSec=1

[Install]
WantedBy=multi-user.target
UNIT
```
<br>

Now enable and start the service
```
sudo systemctl daemon-reload
sudo systemctl enable --now hid-netd.service
systemctl status hid-netd.service --no-pager
```
<br>

you should see **enabled** in green, for the real test Reboot your Pi Zero

Now enable and start the service
```
sudo reboot
```
Reconnect to your Pi Zero via SSH, then validate the following
```
systemctl status usb-gadget-hid.service --no-pager
systemctl status hid-netd.service --no-pager
cat /sys/kernel/config/usb_gadget/g1/UDC
```
you should see lots of green text saying **active** and **enabled** if you do, then you have completed the Pi Zero portion of the setup and the hardest part is all done =)<br><br>
If you have not already, you can power down the Pi Zero via SSH, and plug in your OTG USB cable to middle port on the unit, this is the data port on the Raspberry Pi Zero.
```
sudo shutdown -h now
```
<br>

Finally, to validate everything from top to bottom before moving onto the TTY bridge/emulator, power on the Pi Zero, with the data port connected to either a test PC or a Commodore C64 Ultimate then create and execute a simple test script to validate everything is working perfectly. There are two scripts, one "Hello World" or my personal favourite "I Love My Commodore" :D<br>
**OPTION A: Hello World**
```
cat > hello-world.py <<'PY'
#!/usr/bin/env python3
import json
import os
import socket
import sys

HOST  = os.getenv("C64KBD_PI_HOST", "192.168.1.36")
PORT  = int(os.getenv("C64KBD_PI_PORT", "9999"))
TOKEN = os.getenv("C64KBD_TOKEN", "ILoveMyCommodoreC64")

msg = {
    "token": TOKEN,
    "op": "type",
    "text": "hello world\n",
}

data = (json.dumps(msg) + "\n").encode("utf-8")

try:
    with socket.create_connection((HOST, PORT), timeout=3) as s:
        s.sendall(data)

        # read one line reply (best-effort)
        s.settimeout(3)
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk

        resp = buf.decode("utf-8", errors="ignore").strip()
        print(resp if resp else "OK (no response body)")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PY

chmod +x hello-world.py

```
<br>

**OPTION B: I Love My Commodore** (my personal favourite :D)

```
cat > i-love-my-commodore.py <<'PY'
#!/usr/bin/env python3
import json
import os
import socket
import sys

HOST  = os.getenv("C64KBD_PI_HOST", "192.168.1.36")
PORT  = int(os.getenv("C64KBD_PI_PORT", "9999"))
TOKEN = os.getenv("C64KBD_TOKEN", "ILoveMyCommodoreC64")

# Each line ends with a carriage return (Enter)
program = (
    '10 print "i love my commodore";\n'
    '20 goto 10\n'
    'run\n'
)

msg = {
    "token": TOKEN,
    "op": "type",
    "text": program,
}

data = (json.dumps(msg) + "\n").encode("utf-8")

try:
    with socket.create_connection((HOST, PORT), timeout=3) as s:
        s.sendall(data)

        # read one line reply (best-effort)
        s.settimeout(15)
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk

        resp = buf.decode("utf-8", errors="ignore").strip()
        print(resp if resp else "OK (no response body)")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PY

chmod +x i-love-my-commodore.py

```

<br>

**Note:** In the above two test scripts, we are setting 3 variables that would be unique to your particular setup. You need to adjust/tailor the below lines to suit, **correctly setting the HOST, PORT & TOKEN** variables.
```
HOST  = os.getenv("C64KBD_PI_HOST", "192.168.1.36")
PORT  = int(os.getenv("C64KBD_PI_PORT", "9999"))
TOKEN = os.getenv("C64KBD_TOKEN", "ILoveMyCommodoreC64")
```
<br>



