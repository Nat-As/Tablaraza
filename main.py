#!/usr/bin/env python3
"""
TablaRaza - Enhanced ISO/IMG Flasher
A cross-platform GUI application for flashing ISO and IMG files to USB drives
"""

import sys
import os
import platform
import subprocess
import threading
from pathlib import Path

# GUI imports
try:
    from tkinter import (
        Tk, Frame, Label, Button, Entry, StringVar, 
        messagebox, filedialog, ttk, Canvas, PhotoImage
    )
    from tkinter.font import Font
except ImportError:
    print("Error: tkinter not found. Please install python3-tk")
    sys.exit(1)


class DeviceManager:
    """Cross-platform device detection and management"""
    
    @staticmethod
    def get_devices():
        """Get list of available storage devices"""
        system = platform.system()
        
        if system == "Windows":
            return DeviceManager._get_windows_devices()
        elif system == "Darwin":  # macOS
            return DeviceManager._get_macos_devices()
        elif system == "Linux":
            return DeviceManager._get_linux_devices()
        else:
            return []
    
    @staticmethod
    def _get_windows_devices():
        """Get Windows removable drives"""
        import string
        import ctypes
        
        devices = []
        drives = []
        
        # Get all drive letters
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(letter)
            bitmask >>= 1
        
        # Filter for removable drives
        for drive in drives:
            drive_path = f"{drive}:\\"
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
            
            # 2 = DRIVE_REMOVABLE
            if drive_type == 2:
                try:
                    # Get drive size
                    free_bytes = ctypes.c_ulonglong(0)
                    total_bytes = ctypes.c_ulonglong(0)
                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        drive_path,
                        None,
                        ctypes.pointer(total_bytes),
                        ctypes.pointer(free_bytes)
                    )
                    
                    size_gb = total_bytes.value / (1024**3)
                    devices.append({
                        'path': drive_path,
                        'name': f"{drive}: ({size_gb:.1f} GB)",
                        'size': total_bytes.value
                    })
                except:
                    pass
        
        return devices
    
    @staticmethod
    def _get_macos_devices():
        """Get macOS removable volumes"""
        devices = []
        
        try:
            # Use diskutil to list external disks
            result = subprocess.run(
                ['diskutil', 'list', '-plist', 'external'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Parse diskutil output
                import plistlib
                plist = plistlib.loads(result.stdout.encode())
                
                for disk in plist.get('AllDisksAndPartitions', []):
                    disk_id = disk.get('DeviceIdentifier', '')
                    
                    # Get disk info
                    info_result = subprocess.run(
                        ['diskutil', 'info', '-plist', disk_id],
                        capture_output=True,
                        text=True
                    )
                    
                    if info_result.returncode == 0:
                        info = plistlib.loads(info_result.stdout.encode())
                        size = info.get('TotalSize', 0)
                        size_gb = size / (1024**3)
                        
                        name = info.get('VolumeName', disk_id)
                        
                        devices.append({
                            'path': f"/dev/{disk_id}",
                            'name': f"{name} - /dev/{disk_id} ({size_gb:.1f} GB)",
                            'size': size
                        })
        except Exception as e:
            print(f"Error detecting macOS devices: {e}")
        
        return devices
    
    @staticmethod
    def _get_linux_devices():
        """Get Linux block devices"""
        devices = []
        
        try:
            # Use lsblk to list block devices
            result = subprocess.run(
                ['lsblk', '-b', '-n', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT', '-e', '7,11'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 3:
                        name, size, dev_type = parts[0], parts[1], parts[2]
                        
                        # Only show disk devices (not partitions)
                        if dev_type == 'disk' and not name.startswith('loop'):
                            try:
                                size_bytes = int(size)
                                size_gb = size_bytes / (1024**3)
                                
                                devices.append({
                                    'path': f"/dev/{name}",
                                    'name': f"/dev/{name} ({size_gb:.1f} GB)",
                                    'size': size_bytes
                                })
                            except ValueError:
                                pass
        except Exception as e:
            print(f"Error detecting Linux devices: {e}")
        
        return devices


class FlashManager:
    """Handle the actual flashing process"""
    
    @staticmethod
    def flash_image(image_path, device_path, progress_callback=None):
        """Flash image to device"""
        system = platform.system()
        
        try:
            if system == "Windows":
                return FlashManager._flash_windows(image_path, device_path, progress_callback)
            elif system == "Darwin":
                return FlashManager._flash_macos(image_path, device_path, progress_callback)
            elif system == "Linux":
                return FlashManager._flash_linux(image_path, device_path, progress_callback)
            else:
                raise Exception(f"Unsupported platform: {system}")
        except Exception as e:
            raise Exception(f"Flash error: {str(e)}")
    
    @staticmethod
    def _flash_windows(image_path, device_path, progress_callback):
        """Flash on Windows using direct disk write"""
        import ctypes
        
        if progress_callback:
            progress_callback("Preparing to flash...")
        
        # Extract drive letter
        drive_letter = device_path[0]
        
        # Get physical drive number
        drive_number = FlashManager._get_physical_drive_number(drive_letter)
        if drive_number is None:
            raise Exception("Could not determine physical drive number")
        
        physical_drive = f"\\\\.\\PhysicalDrive{drive_number}"
        
        if progress_callback:
            progress_callback(f"Flashing to {physical_drive}...")
        
        # Open physical drive for writing
        GENERIC_WRITE = 0x40000000
        OPEN_EXISTING = 3
        
        handle = ctypes.windll.kernel32.CreateFileW(
            physical_drive,
            GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            0,
            None
        )
        
        if handle == -1:
            raise Exception("Failed to open device. Try running as administrator.")
        
        try:
            # Read and write image
            chunk_size = 1024 * 1024  # 1MB chunks
            bytes_written = 0
            
            with open(image_path, 'rb') as img:
                file_size = os.path.getsize(image_path)
                
                while True:
                    chunk = img.read(chunk_size)
                    if not chunk:
                        break
                    
                    bytes_to_write = len(chunk)
                    written = ctypes.c_ulong(0)
                    
                    success = ctypes.windll.kernel32.WriteFile(
                        handle,
                        chunk,
                        bytes_to_write,
                        ctypes.byref(written),
                        None
                    )
                    
                    if not success:
                        raise Exception("Write failed")
                    
                    bytes_written += written.value
                    
                    if progress_callback and file_size > 0:
                        percent = (bytes_written / file_size) * 100
                        progress_callback(f"Writing: {percent:.1f}%")
        
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
        
        if progress_callback:
            progress_callback("Flash complete!")
        
        return True
    
    @staticmethod
    def _get_physical_drive_number(drive_letter):
        """Get Windows physical drive number from drive letter"""
        try:
            import wmi
            c = wmi.WMI()
            
            for physical_disk in c.Win32_DiskDrive():
                for partition in physical_disk.associators("Win32_DiskDriveToDiskPartition"):
                    for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                        if logical_disk.Caption == f"{drive_letter}:":
                            return physical_disk.Index
        except:
            pass
        
        return None
    
    @staticmethod
    def _flash_macos(image_path, device_path, progress_callback):
        """Flash on macOS using dd"""
        if progress_callback:
            progress_callback("Unmounting device...")
        
        # Unmount the device
        subprocess.run(['diskutil', 'unmountDisk', device_path], check=False)
        
        if progress_callback:
            progress_callback("Flashing image...")
        
        # Use dd to write image
        # Note: This requires sudo/admin privileges
        result = subprocess.run(
            ['sudo', 'dd', f'if={image_path}', f'of={device_path}', 'bs=1m'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"dd failed: {result.stderr}")
        
        if progress_callback:
            progress_callback("Syncing...")
        
        subprocess.run(['sync'], check=True)
        
        if progress_callback:
            progress_callback("Flash complete!")
        
        return True
    
    @staticmethod
    def _flash_linux(image_path, device_path, progress_callback):
        """Flash on Linux using dd"""
        if progress_callback:
            progress_callback("Unmounting device...")
        
        # Unmount any mounted partitions
        try:
            result = subprocess.run(['mount'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if device_path in line:
                    mount_point = line.split()[2]
                    subprocess.run(['sudo', 'umount', mount_point], check=False)
        except:
            pass
        
        if progress_callback:
            progress_callback("Flashing image...")
        
        # Use dd with status=progress for feedback
        process = subprocess.Popen(
            ['sudo', 'dd', f'if={image_path}', f'of={device_path}', 'bs=4M', 'status=progress'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Monitor progress
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
            
            if line and progress_callback:
                progress_callback(f"Writing: {line.strip()}")
        
        if process.returncode != 0:
            raise Exception("dd failed")
        
        if progress_callback:
            progress_callback("Syncing...")
        
        subprocess.run(['sync'], check=True)
        
        if progress_callback:
            progress_callback("Flash complete!")
        
        return True


class TablaRazaGUI:
    """Main GUI application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("TablaRaza - Image Flasher")
        self.root.geometry("700x500")
        self.root.resizable(False, False)
        
        # Variables
        self.image_path = StringVar()
        self.selected_device = StringVar()
        self.devices = []
        
        # Setup UI
        self._setup_styles()
        self._create_ui()
        
        # Initial device scan
        self.refresh_devices()
    
    def _setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Custom colors
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        accent_color = "#4a9eff"
        button_bg = "#3a3a3a"
        
        self.root.configure(bg=bg_color)
        
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'))
        style.configure('Subtitle.TLabel', font=('Segoe UI', 9), foreground='#aaaaaa')
        
        style.configure('TButton', 
                       background=button_bg, 
                       foreground=fg_color,
                       borderwidth=0,
                       font=('Segoe UI', 10))
        style.map('TButton',
                 background=[('active', accent_color)])
        
        style.configure('Accent.TButton',
                       background=accent_color,
                       foreground=fg_color,
                       font=('Segoe UI', 11, 'bold'))
        style.map('Accent.TButton',
                 background=[('active', '#3a8eef')])
        
        style.configure('TCombobox',
                       fieldbackground=button_bg,
                       background=button_bg,
                       foreground=fg_color,
                       arrowcolor=fg_color)
    
    def _create_ui(self):
        """Create the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding=30)
        main_frame.pack(fill='both', expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill='x', pady=(0, 20))
        
        title = ttk.Label(header_frame, text="TablaRaza", style='Title.TLabel')
        title.pack()
        
        subtitle = ttk.Label(header_frame, 
                            text="Flash ISO & IMG files to USB drives and SD cards",
                            style='Subtitle.TLabel')
        subtitle.pack()
        
        # Image selection section
        image_frame = ttk.LabelFrame(main_frame, text=" Select Image File ", padding=15)
        image_frame.pack(fill='x', pady=(0, 15))
        
        image_path_frame = ttk.Frame(image_frame)
        image_path_frame.pack(fill='x')
        
        self.image_entry = ttk.Entry(image_path_frame, textvariable=self.image_path, 
                                     state='readonly', width=50)
        self.image_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        browse_btn = ttk.Button(image_path_frame, text="Browse...", 
                               command=self.browse_image)
        browse_btn.pack(side='left')
        
        # Device selection section
        device_frame = ttk.LabelFrame(main_frame, text=" Select Target Device ", padding=15)
        device_frame.pack(fill='x', pady=(0, 15))
        
        device_select_frame = ttk.Frame(device_frame)
        device_select_frame.pack(fill='x')
        
        self.device_combo = ttk.Combobox(device_select_frame, 
                                         textvariable=self.selected_device,
                                         state='readonly',
                                         width=47)
        self.device_combo.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        refresh_btn = ttk.Button(device_select_frame, text="Refresh", 
                                command=self.refresh_devices)
        refresh_btn.pack(side='left')
        
        # Warning label
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill='x', pady=(0, 20))
        
        warning_label = ttk.Label(warning_frame,
                                 text="Warning: All data on the selected device will be erased!",
                                 style='Subtitle.TLabel',
                                 foreground='#ff6b6b')
        warning_label.pack()
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(0, 10))
        
        self.flash_btn = ttk.Button(button_frame, text="Flash Image", 
                                    style='Accent.TButton',
                                    command=self.flash_image)
        self.flash_btn.pack(side='left', expand=True, fill='x', padx=(0, 10))
        
        self.format_btn = ttk.Button(button_frame, text="Format Device",
                                     command=self.format_device)
        self.format_btn.pack(side='left', expand=True, fill='x')
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text=" Progress ", padding=15)
        progress_frame.pack(fill='both', expand=True)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=(0, 10))
        
        self.status_label = ttk.Label(progress_frame, text="Ready", 
                                     style='Subtitle.TLabel')
        self.status_label.pack()
        
        # Footer
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill='x', pady=(10, 0))
        
        footer_text = ttk.Label(footer_frame,
                               text="TablaRaza v2.0 - Open Source ISO/IMG Flasher",
                               style='Subtitle.TLabel')
        footer_text.pack()
    
    def browse_image(self):
        """Open file dialog to select image"""
        filename = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[
                ("Image Files", "*.iso *.img"),
                ("ISO Files", "*.iso"),
                ("IMG Files", "*.img"),
                ("All Files", "*.*")
            ]
        )
        
        if filename:
            self.image_path.set(filename)
            self.update_status(f"Selected: {Path(filename).name}")
    
    def refresh_devices(self):
        """Refresh the list of available devices"""
        self.update_status("Scanning for devices...")
        
        self.devices = DeviceManager.get_devices()
        
        if self.devices:
            device_names = [dev['name'] for dev in self.devices]
            self.device_combo['values'] = device_names
            self.device_combo.current(0)
            self.update_status(f"Found {len(self.devices)} device(s)")
        else:
            self.device_combo['values'] = []
            self.update_status("No removable devices found")
    
    def flash_image(self):
        """Start the flashing process"""
        # Validate inputs
        if not self.image_path.get():
            messagebox.showerror("Error", "Please select an image file")
            return
        
        if not self.selected_device.get():
            messagebox.showerror("Error", "Please select a target device")
            return
        
        # Confirm action
        response = messagebox.askyesno(
            "Confirm Flash",
            f"This will erase all data on {self.selected_device.get()}\n\n"
            "Are you sure you want to continue?"
        )
        
        if not response:
            return
        
        # Get selected device path
        device_idx = self.device_combo.current()
        device_path = self.devices[device_idx]['path']
        
        # Disable buttons
        self.flash_btn.config(state='disabled')
        self.format_btn.config(state='disabled')
        
        # Start progress bar
        self.progress_bar.start()
        
        # Run flashing in thread
        thread = threading.Thread(
            target=self._flash_thread,
            args=(self.image_path.get(), device_path),
            daemon=True
        )
        thread.start()
    
    def _flash_thread(self, image_path, device_path):
        """Thread function for flashing"""
        try:
            FlashManager.flash_image(image_path, device_path, self.update_status)
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                "Image flashed successfully!"
            ))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "Error",
                f"Flash failed: {str(e)}"
            ))
        
        finally:
            self.root.after(0, self._flash_complete)
    
    def _flash_complete(self):
        """Re-enable UI after flashing"""
        self.progress_bar.stop()
        self.flash_btn.config(state='normal')
        self.format_btn.config(state='normal')
        self.update_status("Ready")
    
    def format_device(self):
        """Format the selected device"""
        if not self.selected_device.get():
            messagebox.showerror("Error", "Please select a device to format")
            return
        
        response = messagebox.askyesno(
            "Confirm Format",
            f"This will erase all data on {self.selected_device.get()}\n\n"
            "Are you sure you want to continue?"
        )
        
        if not response:
            return
        
        device_idx = self.device_combo.current()
        device_path = self.devices[device_idx]['path']
        
        self.update_status("Formatting device...")
        self.progress_bar.start()
        
        thread = threading.Thread(
            target=self._format_thread,
            args=(device_path,),
            daemon=True
        )
        thread.start()
    
    def _format_thread(self, device_path):
        """Thread function for formatting"""
        try:
            system = platform.system()
            
            if system == "Windows":
                drive_letter = device_path[0]
                subprocess.run(['format', f'{drive_letter}:', '/FS:FAT32', '/Q', '/Y'],
                             check=True, shell=True)
            
            elif system == "Darwin":
                subprocess.run(['diskutil', 'eraseDisk', 'FAT32', 'TABLARAZA', device_path],
                             check=True)
            
            elif system == "Linux":
                subprocess.run(['sudo', 'mkfs.vfat', '-F', '32', device_path],
                             check=True)
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                "Device formatted successfully!"
            ))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "Error",
                f"Format failed: {str(e)}"
            ))
        
        finally:
            self.root.after(0, self._format_complete)
    
    def _format_complete(self):
        """Re-enable UI after formatting"""
        self.progress_bar.stop()
        self.update_status("Ready")
        self.refresh_devices()
    
    def update_status(self, message):
        """Update status label"""
        self.root.after(0, lambda: self.status_label.config(text=message))


def main():
    """Main entry point"""
    # Check if running on macOS and warn about permissions
    if platform.system() == "Darwin":
        print("Note: On macOS, you may be prompted for administrator password")
    
    # Check if running on Linux and warn about permissions
    if platform.system() == "Linux":
        if os.geteuid() != 0:
            print("Note: On Linux, you may need to run with sudo for device access")
    
    root = Tk()
    app = TablaRazaGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()