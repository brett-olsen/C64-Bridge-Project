# C64-Bridge-Project
A repo for the C64 Bridge Project, a wireless USB Keyboard/HID emulator for the Raspberry Pi Zero W2, with a Serial Emulator bridge (can be used with the VibeC64 Project, see https://github.com/bbence84/VibeC64)<br><br>

**What is this Project?**<br>
This project is designed to allow for the remote transmission of keyboard strokes from a host computer, to the Raspberry Pi Zero W2, which then emulates a HID keyboard via gadget mode, and relays those keystrokes to the Commodore C64 Ultimate (see https://www.commodore.net/), while this project can have a myriad of uses, it is specifically designed to be a drop in, zero code additon to the VibeC64 Project (see https://github.com/bbence84/VibeC64) this then effectively gives VibeC64 the ability to remotely control the physical C64 Ultimate computer, coupled with a webcam, this allows VibeC64 to monitor, control and test basic applications plus games on a physical C64 ultimate<br><br>

**Hardware**<br>
1 x Pi Zero 2 W<br>
1 x micro-USB data cable<br>
1 x OTG micro-USB shim<br>
1 x micro SD card (at least 4gb)<br><br>

Optional<br>
1 x micro-USB cable for power/setup<br><br>
**NOTE: Be careful with physical connections, typically I used a USB powersupply or a USB battery pack to keep the PI running during configuration, while I am not an electronics engineer, I believe it is best practice to not have multiple cables connected, for example, do not power the Pi Zero and simultaniously connect a data cable to another computer unless you know what you are doing. During set-up, 1 cable for power, during testing and during operation 1 cable for data/power seems to work well for this project. Be careful with your connections and devices! TLDR only use 1 cable at a time =)**<br><br>

# Getting it up & running<br><br>
**1) Flash the Raspberry PI OS**<br>
I personally used the Raspberry PI imager over at https://github.com/raspberrypi/rpi-imager, however any of the popular Raspberry PI flashing tools will work (see https://www.raspberrypi.com/software/), for a number of reasons and for increased compatibility I used the following image:<br><br>

- Raspberry Pi OS Lite (32-bit) (see https://www.raspberrypi.com/software/operating-systems/)<br>
When flashing the Pi OS be sure to set the following:<br>
- Device - If asked, choose the correct device, in this case a Raspberry Pi Zero 2 W
- If the flashing app has the option, you may need to choose other OS or choose the image you downloaded, again ensure it is the Pi OS Lite 32 bit
- Hostname: PiZero2W (choose your own, this is what I chose and will be reffered to herein)<br>
- Enable: SSH (if asked, I used password authentication)<br>
- Configure Wi-FI with a SSID/password, set your country<br>
- Set a username/password<br><br>
When the flashing of the PI Os image has completed, insert the SD card and power on the PI.<br><br>

**2) Getting the PI Zero 2 W Running**<br>
Note: First boot of the PI Zero 2 W may take some time, be paitent =)<br><br>
Find the IP address of the PI Zero from your router, or if MDNS works SSH into your PI Zero
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
(this will take some time, but its a good idea to get your packages up to date)<br>
<br>

Configure the PI Zero, for gadget mode
```
sudo nano /boot/firmware/config.txt
```
<br>

In the [all] section, make the following addition (typically at the end of the file)<br>
```
dtoverlay=dwc2,dr_mode=peripheral
```
<br>

ensure the required kernel modules load at boot
```
echo -e "dwc2\nlibcomposite" | sudo tee /etc/modules-load.d/usb-gadget.conf >/dev/null
```
<br>

make the configfs mount persistent, add configfs to /etc/fstab
```
echo "configfs  /sys/kernel/config  configfs  defaults  0  0" | sudo tee -a /etc/fstab >/dev/null
```
<br>

reboot your PI Zero
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

**3) Configure USB Gadget mode**<br>
On the PI Zero, create /usr/local/sbin/gadget-hid-up.sh either manually or using the following script
```
sudo tee /usr/local/sbin/gadget-hid-up.sh >/dev/null <<'SH'
#!/usr/bin/env bash
set -euo pipefail

G=/sys/kernel/config/usb_gadget/g1

# Ensure configfs is mounted
mountpoint -q /sys/kernel/config || mount -t configfs none /sys/kernel/config

modprobe libcomposite >/dev/null 2>&1 || true

mkdir -p "$G"
cd "$G"

# USB IDs (safe defaults). You can change later.
echo 0x1d6b > idVendor   # Linux Foundation (common for gadgets)
echo 0x0104 > idProduct  # Multifunction Composite Gadget

mkdir -p strings/0x409
echo "PiZero2W"            > strings/0x409/serialnumber
echo "PiZero2W Serial+HID" > strings/0x409/product
echo "PiZero2W"            > strings/0x409/manufacturer

mkdir -p configs/c.1/strings/0x409
echo "Config 1: HID Keyboard (+Serial)" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower

# ---- HID keyboard function ----
mkdir -p functions/hid.usb0
echo 1 > functions/hid.usb0/protocol    # keyboard
echo 1 > functions/hid.usb0/subclass    # boot interface subclass
echo 8 > functions/hid.usb0/report_length

# Standard 8-byte boot keyboard report descriptor
cat > functions/hid.usb0/report_desc <<'DESC'
\x05\x01\x09\x06\xa1\x01\x05\x07\x19\xe0\x29\xe7\x15\x00\x25\x01\x75\x01\x95\x08\x81\x02\x95\x01\x75\x08\x81\x01\x95\x05\x75\x01\x05\x08\x19\x01\x29\x05\x91\x02\x95\x01\x75\x03\x91\x01\x95\x06\x75\x08\x15\x00\x25\x65\x05\x07\x19\x00\x29\x65\x81\x00\xc0
DESC

ln -sf functions/hid.usb0 configs/c.1/

# ---- Optional ACM serial function (handy for debugging) ----
# Comment these 2 lines out if you *only* want keyboard.
mkdir -p functions/acm.usb0
ln -sf functions/acm.usb0 configs/c.1/

# Bind to UDC
UDC="$(ls /sys/class/udc | head -n1)"
echo "$UDC" > UDC

echo "UP: bound to UDC=$UDC"
SH

sudo chmod +x /usr/local/sbin/gadget-hid-up.sh
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

On the PI Zero, enable and start the service, check for errors as you do this
```
sudo systemctl daemon-reload
sudo systemctl enable --now usb-gadget-hid.service
systemctl status usb-gadget-hid.service --no-pager
```
You should see **active** and **enabled** in green (if your terminal supports colors)
<br><br>

Verify all is working, on the PI Zero
```
sudo reboot
```
then re-connect and execute:
```
cat /sys/kernel/config/usb_gadget/g1/UDC
```
If all is working, you should see an output similar to **3f980000.usb**<br><br>





