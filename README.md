# Monitor-Switcher
To switch between monitors, you need to use this script.

Prerequisites:
Gnome
Wayland
Python 3


Step 1: Get a List of Monitors
Run the following command to list the available monitors:

```bash
gnome-monitor-config list
```

Step 2: Update the Script
Modify the script to match your dummy plug name:

```python
config = {
    'idle_threshold': 900000,  # Default: 15 minutes
    'primary_monitor_name': 'Telecom Technology Centre Co. Ltd. 23"',  # Default display name
    'monitor_mode': '1280x720@60.000'
}
```

My dummy plug name is "Telecom Technology Centre Co. Ltd. 23".

The script will switch to the dummy plug after 15 minutes (900,000 milliseconds) of inactivity.

Step 3: Switching Back
To exit the remote display:

Enter your password and log in.
Set a shortcut key to switch back to your main monitor.
Step 4: Enable the Required Gnome Extension
Ensure this extension is activated in Gnome Shell:
gnome-shell-extension-unblank

Step 5: Configure System Settings
Run the following commands to set the required system variables:

```bash
gsettings set org.gnome.desktop.screensaver idle-activation-enabled false
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power idle-brightness 100
```

Step 6: Disable Sleep Mode
To completely disable sleep mode on your computer, run:

```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

and in the end make this python code to run after each restart to do that first install dependencies with pip
```bash
pip install PyGObject
```

then go to this address ```/home/youruser/.config/autostart``` 

and make a desktop file for it

```
[Desktop Entry]
Type=Application
Name=Display Switcher on Wayland
Exec=/usr/bin/python3 /data/services/display/wayland.py
Comment=Automatically switches display when idle
Actions=RunInTerminal;


[Desktop Action RunInTerminal]
Name=Run in Terminal
Icon=application-x-executable
```
