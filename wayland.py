#!/usr/bin/env python3
#/usr/bin/python3 /data/Workspace/Services/display/wayland.py
import time
import subprocess
import logging
import logging.handlers
import os
from gi.repository import GLib, Gio

def setup_logging():
    """Set up rotating log files"""
    log_dir = os.path.expanduser('~/.local/share/display_switcher')
    os.makedirs(log_dir, exist_ok=True)
    
    handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'display_switcher.log'),
        maxBytes=1024*1024,  # 1MB
        backupCount=3
    )
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add console handler too
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.addHandler(console_handler)

def load_config():
    """Load configuration from file"""
    config = {
        'idle_threshold': 900000,  # Default: 15 minutes
        'primary_monitor_name': 'Telecom Technology Centre Co. Ltd. 23"',  # Default display name
        'monitor_mode': '1280x720@60.000'
    }
    
    config_path = os.path.expanduser('~/.config/display_switcher.conf')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        if key.strip() == 'idle_threshold':
                            config['idle_threshold'] = int(value.strip())
                        elif key.strip() == 'primary_monitor_name':
                            config['primary_monitor_name'] = value.strip()
                        elif key.strip() == 'monitor_mode':
                            config['monitor_mode'] = value.strip()
            logging.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
    else:
        logging.info(f"No config file found at {config_path}, using defaults")
    
    return config


def get_idle_time():
    """Get the system idle time in milliseconds using GDBus"""
    try:
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        result = connection.call_sync(
            'org.gnome.Mutter.IdleMonitor',
            '/org/gnome/Mutter/IdleMonitor/Core',
            'org.gnome.Mutter.IdleMonitor',
            'GetIdletime',
            None,
            GLib.VariantType('(t)'),
            Gio.DBusCallFlags.NONE,
            -1,
            None
        )
        idle_time = result.unpack()[0]
        return idle_time
    except Exception as e:
        logging.error(f"Error getting idle time: {e}")
        return 0


def get_monitor_port_by_name(display_name):
    """Find the monitor port (DP-X, HDMI-X) by display name"""
    try:
        result = subprocess.run(["gnome-monitor-config", "list"], capture_output=True, text=True)
        if result.returncode != 0:
            logging.error(f"Failed to get monitor list: {result.stderr}")
            return None
            
        output = result.stdout
        current_port = None
        
        for line in output.splitlines():
            line = line.strip()
            
            # Check for monitor port line
            if line.startswith("Monitor ["):
                current_port = line.split("[")[1].split("]")[0].strip()
            
            # Check for display name
            elif "display-name:" in line and display_name in line:
                logging.info(f"Found monitor '{display_name}' at port {current_port}")
                return current_port
                
        logging.error(f"Could not find monitor with display name: {display_name}")
        return None
    except Exception as e:
        logging.error(f"Error finding monitor by name: {e}")
        return None



def switch_display(monitor_name, mode):
    """Switch to the specified display using gnome-monitor-config"""
    try:
        # Find the correct port for the monitor name
        monitor_port = get_monitor_port_by_name(monitor_name)
        
        if not monitor_port:
            logging.error(f"Could not find port for monitor: {monitor_name}")
            return False
            
        cmd = [
            "gnome-monitor-config", 
            "set", 
            "--logical-monitor", 
            "--x=0", 
            "--y=0", 
            "--primary", 
            f"--monitor={monitor_port}", 
            f"--mode={mode}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"Successfully switched display to {monitor_name} ({monitor_port}, {mode})")
            return True
        else:
            logging.error(f"Failed to switch display: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"Error switching display: {e}")
        return False


def lock_screen():
    """Lock the screen using loginctl"""
    try:
        cmd = ["loginctl", "lock-session"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("Successfully locked the screen")
            return True
        else:
            logging.error(f"Failed to lock the screen: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"Error locking the screen: {e}")
        return False

def setup_idle_monitor(idle_threshold, config):
    """Set up idle monitor with a watch for the threshold"""
    try:
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        result = connection.call_sync(
            'org.gnome.Mutter.IdleMonitor',
            '/org/gnome/Mutter/IdleMonitor/Core',
            'org.gnome.Mutter.IdleMonitor',
            'AddIdleWatch',
            GLib.Variant('(t)', [idle_threshold]),
            GLib.VariantType('(u)'),
            Gio.DBusCallFlags.NONE,
            -1,
            None
        )
        watch_id = result.unpack()[0]
        logging.info(f"Set up idle watch with ID: {watch_id} for {idle_threshold}ms")
        return watch_id, connection
    except Exception as e:
        logging.error(f"Error setting up idle monitor: {e}")
        return None, None

def remove_watch(connection, watch_id):
    """Remove a watch by ID"""
    try:
        connection.call_sync(
            'org.gnome.Mutter.IdleMonitor',
            '/org/gnome/Mutter/IdleMonitor/Core',
            'org.gnome.Mutter.IdleMonitor',
            'RemoveWatch',
            GLib.Variant('(u)', [watch_id]),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None
        )
        logging.info(f"Removed watch with ID: {watch_id}")
        return True
    except Exception as e:
        logging.error(f"Error removing watch {watch_id}: {e}")
        return False

def setup_activity_watch(config):
    """Set up a watch for when user becomes active again"""
    try:
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        # AddUserActiveWatch has no parameters
        result = connection.call_sync(
            'org.gnome.Mutter.IdleMonitor',
            '/org/gnome/Mutter/IdleMonitor/Core',
            'org.gnome.Mutter.IdleMonitor',
            'AddUserActiveWatch',
            None,
            GLib.VariantType('(u)'),
            Gio.DBusCallFlags.NONE,
            -1,
            None
        )
        watch_id = result.unpack()[0]
        logging.info(f"Set up activity watch with ID: {watch_id}")
        return watch_id, connection
    except Exception as e:
        logging.error(f"Error setting up activity watch: {e}")
        return None, None

def main():
    """Main function to monitor idle time using event-based approach"""
    setup_logging()
    logging.info("Starting display switcher")
    
    # Load configuration
    config = load_config()
    idle_threshold = config['idle_threshold']
    
    # State tracking variables
    idle_watch_id = None
    active_watch_id = None
    display_switched = False
    
    # Set up the main loop
    loop = GLib.MainLoop()
    
    def on_idle_watch_triggered(connection, sender_name, object_path, interface_name, signal_name, parameters, user_data):
        """Callback when idle threshold is reached"""
        nonlocal display_switched, idle_watch_id
        watch_id = parameters.unpack()[0]
        
        if watch_id != idle_watch_id:
            return
            
        logging.info(f"Idle watch triggered: {watch_id}")
        
        # Always switch to Telecom monitor when idle, regardless of display_switched state
        if switch_display(config['primary_monitor_name'], config['monitor_mode']):
            lock_screen()
            display_switched = True


    
    def on_user_active(connection, sender_name, object_path, interface_name, signal_name, parameters, user_data):
        """Callback when user becomes active"""
        nonlocal display_switched, active_watch_id
        watch_id = parameters.unpack()[0]
        
        if watch_id != active_watch_id:
            return
            
        logging.info(f"User became active, watch ID: {watch_id}")
        
        if display_switched:
            display_switched = False
            logging.info("Display state reset due to user activity")
    
    try:
        # Set up connection
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        
        # Set up idle watch
        idle_watch_result = connection.call_sync(
            'org.gnome.Mutter.IdleMonitor',
            '/org/gnome/Mutter/IdleMonitor/Core',
            'org.gnome.Mutter.IdleMonitor',
            'AddIdleWatch',
            GLib.Variant('(t)', [idle_threshold]),
            GLib.VariantType('(u)'),
            Gio.DBusCallFlags.NONE,
            -1,
            None
        )
        idle_watch_id = idle_watch_result.unpack()[0]
        logging.info(f"Set up idle watch with ID: {idle_watch_id} for {idle_threshold}ms")
        
        # Set up activity watch
        active_watch_result = connection.call_sync(
            'org.gnome.Mutter.IdleMonitor',
            '/org/gnome/Mutter/IdleMonitor/Core',
            'org.gnome.Mutter.IdleMonitor',
            'AddUserActiveWatch',
            None,
            GLib.VariantType('(u)'),
            Gio.DBusCallFlags.NONE,
            -1,
            None
        )
        active_watch_id = active_watch_result.unpack()[0]
        logging.info(f"Set up activity watch with ID: {active_watch_id}")
        
        # Connect to the WatchFired signal for both watches
        connection.signal_subscribe(
            'org.gnome.Mutter.IdleMonitor',
            'org.gnome.Mutter.IdleMonitor',
            'WatchFired',
            '/org/gnome/Mutter/IdleMonitor/Core',
            None,
            Gio.DBusSignalFlags.NONE,
            on_idle_watch_triggered,
            None
        )
        
        connection.signal_subscribe(
            'org.gnome.Mutter.IdleMonitor',
            'org.gnome.Mutter.IdleMonitor',
            'WatchFired',
            '/org/gnome/Mutter/IdleMonitor/Core',
            None,
            Gio.DBusSignalFlags.NONE,
            on_user_active,
            None
        )

        # ADD THE NEW CODE HERE
        def on_screen_locked(connection, sender_name, object_path, interface_name, signal_name, parameters):
            """Handle screen lock events"""
            logging.info("Screen locked - ensuring display configuration")
            switch_display(config['primary_monitor_name'], config['monitor_mode'])

        def on_screen_unlocked(connection, sender_name, object_path, interface_name, signal_name, parameters):
            """Handle screen unlock events"""
            logging.info("Screen unlocked - resetting display state")
            nonlocal display_switched
            display_switched = False

        # Subscribe to screen lock/unlock signals
        session_bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        session_bus.signal_subscribe(
            "org.gnome.ScreenSaver",
            "org.gnome.ScreenSaver",
            "ActiveChanged",
            "/org/gnome/ScreenSaver",
            None,
            Gio.DBusSignalFlags.NONE,
            lambda conn, sender, path, iface, signal, params: 
                on_screen_locked(conn, sender, path, iface, signal, params) if params.unpack()[0] else 
                on_screen_unlocked(conn, sender, path, iface, signal, params)
        )
        
        # Run the main loop
        logging.info(f"Monitoring idle time with threshold of {idle_threshold}ms")
        loop.run()
        
    except KeyboardInterrupt:
        logging.info("Display switcher stopped by user")
    except Exception as e:
        logging.error(f"Error in main loop: {e}")
    finally:
        # Clean up watches if they exist
        if idle_watch_id is not None:
            remove_watch(connection, idle_watch_id)
        if active_watch_id is not None:
            remove_watch(connection, active_watch_id)
        logging.info("Display switcher shutdown complete")

if __name__ == "__main__":
    main()
