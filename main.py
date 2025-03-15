# -*- coding: utf-8 -*-
"""
Created on Wed Mar 12 15:15:39 2025

@author: Nat-As
"""

import os
import sys
import platform
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import psutil

class ISOFlasher(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("ISO Flasher")
        self.geometry("800x600")
        self.minsize(700, 500)
        
        # Set theme colors
        self.primary_color = "#2563eb"  # Blue
        self.secondary_color = "#f3f4f6"  # Light gray
        self.background_color = "#ffffff"  # White
        self.text_color = "#1f2937"  # Dark gray
        self.success_color = "#10b981"  # Green
        self.error_color = "#ef4444"  # Red
        
        self.configure(bg=self.background_color)
        
        self.iso_path = tk.StringVar()
        self.selected_device = tk.StringVar()
        self.format_device = tk.BooleanVar(value=True)
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready to flash")
        
        # Store sudo password for macOS
        self.sudo_password = None
        
        self.create_widgets()
        self.update_device_list()
    
    def create_widgets(self):
        # Create a frame for the main content
        main_frame = tk.Frame(self, bg=self.background_color, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # App title
        title_frame = tk.Frame(main_frame, bg=self.background_color)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            title_frame, 
            text="ISO Flasher", 
            font=("Helvetica", 24, "bold"), 
            fg=self.primary_color,
            bg=self.background_color
        )
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(
            title_frame, 
            text="Flash ISO images to SD cards and USB drives", 
            font=("Helvetica", 12), 
            fg=self.text_color,
            bg=self.background_color
        )
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0), pady=(10, 0))
        
        # File selection section
        file_frame = tk.LabelFrame(
            main_frame, 
            text="Select ISO File", 
            font=("Helvetica", 12, "bold"),
            fg=self.text_color,
            bg=self.background_color,
            padx=10,
            pady=10
        )
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.iso_entry = tk.Entry(
            file_frame, 
            textvariable=self.iso_path,
            font=("Helvetica", 10),
            width=50,
            bg=self.secondary_color,
            fg=self.text_color
        )
        self.iso_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_button = ttk.Button(
            file_frame, 
            text="Browse", 
            command=self.browse_iso,
            style="TButton"
        )
        browse_button.pack(side=tk.RIGHT)
        
        # Device selection section
        device_frame = tk.LabelFrame(
            main_frame, 
            text="Select Target Device", 
            font=("Helvetica", 12, "bold"),
            fg=self.text_color,
            bg=self.background_color,
            padx=10,
            pady=10
        )
        device_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.device_combo = ttk.Combobox(
            device_frame, 
            textvariable=self.selected_device,
            font=("Helvetica", 10),
            state="readonly"
        )
        self.device_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        refresh_button = ttk.Button(
            device_frame, 
            text="Refresh", 
            command=self.update_device_list
        )
        refresh_button.pack(side=tk.RIGHT)
        
        # Format option
        format_frame = tk.Frame(main_frame, bg=self.background_color, pady=5)
        format_frame.pack(fill=tk.X)
        
        format_check = ttk.Checkbutton(
            format_frame, 
            text="Format device before flashing (recommended)", 
            variable=self.format_device
        )
        format_check.pack(anchor=tk.W)
        
        # Warning
        warning_frame = tk.Frame(main_frame, bg="#ffedd5", padx=10, pady=10)  # Light orange bg
        warning_frame.pack(fill=tk.X, pady=(0, 15))
        
        warning_label = tk.Label(
            warning_frame, 
            text="Warning: All data on the selected device will be erased during the flash process!", 
            fg="#9a3412",  # Dark orange text
            bg="#ffedd5",
            font=("Helvetica", 10, "bold"),
            wraplength=700
        )
        warning_label.pack()
        
        # Progress section
        progress_frame = tk.Frame(main_frame, bg=self.background_color)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            mode="determinate",
            length=100
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        status_label = tk.Label(
            progress_frame, 
            textvariable=self.status_var,
            fg=self.text_color,
            bg=self.background_color
        )
        status_label.pack(anchor=tk.W)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg=self.background_color)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.flash_button = ttk.Button(
            button_frame, 
            text="Flash ISO", 
            command=self.flash_iso,
            style="Accent.TButton"
        )
        self.flash_button.pack(side=tk.RIGHT)
        
        cancel_button = ttk.Button(
            button_frame, 
            text="Exit", 
            command=self.cancel
        )
        cancel_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Helvetica", 10))
        self.style.configure("Accent.TButton", font=("Helvetica", 10, "bold"))
        self.style.map("Accent.TButton",
                  foreground=[('pressed', self.background_color), ('active', self.background_color)],
                  background=[('pressed', '!disabled', self.primary_color), ('active', self.primary_color)]
                  )
    
    def browse_iso(self):
        file_path = filedialog.askopenfilename(
            title="Select ISO File",
            filetypes=(("ISO files", "*.iso"), ("All files", "*.*"))
        )
        if file_path:
            self.iso_path.set(file_path)
    
    def update_device_list(self):
        devices = []
        
        if platform.system() == "Windows":
            # Get drives with Win32_DiskDrive
            try:
                # For Windows, list logical drives
                import win32api
                drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
                for drive in drives:
                    if drive.startswith('C:') or drive.startswith('S:'):  # Skip
                        continue
                    try:
                        info = psutil.disk_usage(drive)
                        size_gb = info.total / (1024**3)
                        device_name = f"{drive} ({size_gb:.1f} GB)"
                        devices.append((device_name, drive))
                    except:
                        pass
            except:
                messagebox.showwarning("Warning", "Could not retrieve device information on Windows.")
        
        elif platform.system() == "Linux":
            # For Linux, use lsblk to get block devices
            try:
                output = subprocess.check_output(["lsblk", "-d", "-o", "NAME,SIZE,MODEL,TRAN", "-n"]).decode("utf-8")
                for line in output.splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        device_name = parts[0]
                        size = parts[1]
                        model = " ".join(parts[2:-1]) if len(parts) > 3 else ""
                        transport = parts[-1] if len(parts) > 2 else ""
                        
                        # Only include removable devices (not internal hard drives)
                        if (transport == "usb" or (
                                device_name.startswith(("sd", "mmcblk")) and not device_name.startswith("sda"))):
                            full_path = f"/dev/{device_name}"
                            display_name = f"{full_path} ({size}{', ' + model if model else ''})"
                            devices.append((display_name, full_path))
            except:
                messagebox.showwarning("Warning", "Could not retrieve device information on Linux.")
        
        elif platform.system() == "Darwin":  # macOS
            try:
                # For macOS, use diskutil list
                output = subprocess.check_output(["diskutil", "list", "external"], universal_newlines=True)
                current_disk = None
                
                for line in output.splitlines():
                    if line.startswith("/dev/"):
                        current_disk = line.split()[0]
                        # Get disk info
                        try:
                            info = subprocess.check_output(["diskutil", "info", current_disk], universal_newlines=True)
                            size = ""
                            name = ""
                            
                            for info_line in info.splitlines():
                                if "Disk Size" in info_line:
                                    size = info_line.split(":", 1)[1].strip()
                                if "Volume Name" in info_line:
                                    name = info_line.split(":", 1)[1].strip()
                            
                            display_name = f"{current_disk} ({size}{', ' + name if name else ''})"
                            devices.append((display_name, current_disk))
                        except:
                            pass
            except:
                messagebox.showwarning("Warning", "Could not retrieve device information on macOS.")
        
        # Update combobox with device list
        if devices:
            print(devices)
            self.device_combo['values'] = [name for name, _ in devices]
            self.device_paths = {name: path for name, path in devices}
            self.device_combo.current(0)
        else:
            self.device_combo['values'] = ["No removable devices found"]
            self.device_paths = {}
            self.device_combo.current(0)
    
    def get_device_path(self):
        selected = self.selected_device.get()
        return self.device_paths.get(selected, "")
    
    def cancel(self):
        sys.exit()
    
    def flash_iso(self):
        iso_path = self.iso_path.get()
        device_path = self.get_device_path()
        
        if not iso_path:
            messagebox.showerror("Error", "Please select an ISO file.")
            return
        
        if not device_path:
            messagebox.showerror("Error", "Please select a valid target device.")
            return
        
        if not os.path.exists(iso_path):
            messagebox.showerror("Error", "The selected ISO file does not exist.")
            return
        
        # Confirm flashing
        confirmation = messagebox.askokcancel(
            "Confirm Flashing", 
            f"You are about to flash:\n\n"
            f"ISO: {iso_path}\n"
            f"To Device: {device_path}\n\n"
            f"This will ERASE ALL DATA on the selected device!\n\n"
            f"Do you want to continue?"
        )
        
        if not confirmation:
            return
        
        # Disable controls during flashing
        self.flash_button.configure(state="disabled")
        self.device_combo.configure(state="disabled")
        self.iso_entry.configure(state="disabled")
        
        # Reset progress
        self.progress_var.set(0)
        self.status_var.set("Preparing...")
        
        # Start flashing in a separate thread
        thread = threading.Thread(target=self.flash_process, args=(iso_path, device_path))
        thread.daemon = True
        thread.start()
    
    def flash_process(self, iso_path, device_path):
        try:
            # 1. Format device if requested
            if self.format_device.get():
                self.update_status("Formatting device...", 10)
                
                if platform.system() == "Windows":
                    # On Windows, use format command
                    drive_letter = device_path.split(':')[0] + ':'
                    subprocess.run(
                        f"format {drive_letter} /fs:NTFS /q /y", 
                        shell=True, 
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                elif platform.system() == "Linux":
                    # On Linux, use mkfs.ntfs
                    subprocess.run(
                        ["sudo", "mkfs.ntfs", "-f", device_path], 
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                elif platform.system() == "Darwin":  # macOS
                    # On macOS, use diskutil
                    subprocess.run(
                        ["diskutil", "eraseDisk", "MS-DOS", "FLASHDRIVE", device_path], 
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                
                self.update_status("Formatting complete", 20)
            
            # 2. Flash ISO to device
            self.update_status("Flashing ISO to device...", 25)
            
            # The actual flashing process varies by platform
            if platform.system() == "Windows":
                # On Windows, use dd for Windows if available, otherwise use a straight file copy
                try:
                    subprocess.run(
                        f"dd if=\"{iso_path}\" of=\\\\.\\{device_path} bs=4M status=progress",
                        shell=True,
                        check=True
                    )
                except:
                    # Fallback to PowerShell method
                    ps_cmd = f'$source = [System.IO.File]::OpenRead("{iso_path}"); '
                    drive_letter = device_path.rstrip('\\')
                    ps_cmd += f'$dest = [System.IO.File]::OpenWrite("\\\\.\\{drive_letter}"); '
                    ps_cmd += '$buffer = New-Object byte[] 4MB; '
                    ps_cmd += '$total = $source.Length; '
                    ps_cmd += '$count = 0; '
                    ps_cmd += 'while(($read = $source.Read($buffer, 0, $buffer.Length)) -gt 0) {'
                    ps_cmd += '$dest.Write($buffer, 0, $read); '
                    ps_cmd += '$count += $read; '
                    ps_cmd += 'Write-Progress -Activity "Copying ISO" -Status "Progress:" -PercentComplete ($count/$total*100); '
                    ps_cmd += '}'
                    ps_cmd += '$source.Close(); $dest.Close();'
                    
                    print("Running powershell command:")
                    print(ps_cmd)
                    subprocess.run(
                        ["powershell", "-Command", ps_cmd],
                        check=True
                    )
            
            elif platform.system() == "Linux":
                # On Linux, use dd command
                process = subprocess.Popen(
                    ["sudo", "dd", f"if={iso_path}", f"of={device_path}", "bs=4M", "status=progress"], 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                
                # Update progress based on dd output
                for line in iter(process.stdout.readline, ""):
                    if "bytes" in line:
                        try:
                            # Extract progress information
                            bytes_copied = int(line.split("bytes")[0].strip())
                            iso_size = os.path.getsize(iso_path)
                            progress = min(90, int(bytes_copied / iso_size * 100))
                            self.update_status(f"Flashing: {progress}% complete", progress)
                        except:
                            pass
                
                process.wait()
                if process.returncode != 0:
                    raise Exception("dd command failed")
            
            elif platform.system() == "Darwin":  # macOS
                # On macOS, use dd command
                # First, unmount but don't eject the disk
                subprocess.run(
                    ["diskutil", "unmountDisk", device_path],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Then use dd to write the ISO
                process = self.run_with_sudo(
                    ["dd", f"if={iso_path}", f"of={device_path}", "bs=4m"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # macOS dd doesn't have progress, so we'll update based on time
                import time
                start_time = time.time()
                iso_size = os.path.getsize(iso_path)
                
                while process.poll() is None:
                    # Estimate progress based on elapsed time (not accurate but provides feedback)
                    elapsed = time.time() - start_time
                    estimated_progress = min(85, int(elapsed / (iso_size / (4 * 1024 * 1024) * 0.5) * 100))
                    self.update_status(f"Flashing in progress... (estimate: {estimated_progress}%)", estimated_progress)
                    time.sleep(1)
                
                if process.returncode != 0:
                    stderr = process.stderr.read().decode('utf-8')
                    raise Exception(f"dd command failed: {stderr}")
            
            # 3. Finalize and sync
            self.update_status("Finalizing and syncing...", 95)
            
            if platform.system() in ["Linux", "Darwin"]:
                if platform.system() == "Darwin":
                    self.run_with_sudo(["sync"], check=True)
                else:
                    subprocess.run(["sync"], check=True)
            
            # 4. Complete
            self.update_status("Flash completed successfully!", 100)
            messagebox.showinfo("Success", "ISO has been successfully flashed to the device!")
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}", 0)
            messagebox.showerror("Error", f"An error occurred during the flashing process:\n\n{str(e)}")
        
        finally:
            # Re-enable controls
            self.after(0, self.enable_controls)
    
    def update_status(self, message, progress):
        self.after(0, lambda: self.status_var.set(message))
        self.after(0, lambda: self.progress_var.set(progress))
    
    def enable_controls(self):
        self.flash_button.configure(state="normal")
        self.device_combo.configure(state="readonly")
        self.iso_entry.configure(state="normal")

    def get_sudo_password(self):
        """Request sudo password using OSA script dialog on macOS"""
        if platform.system() != "Darwin" or self.sudo_password:
            return True
            
        try:
            # Create AppleScript to show password dialog
            script = '''
            tell application "System Events"
                display dialog "Administrator privileges are required to flash the device." & return & return & "Please enter your password:" with title "ISO Flasher" default answer "" with hidden answer buttons {"Cancel", "OK"} default button "OK" with icon caution
                if button returned of result is "OK" then
                    return text returned of result
                else
                    return ""
                end if
            end tell
            '''
            
            # Run AppleScript and get the password
            proc = subprocess.run(['osascript', '-e', script], 
                                capture_output=True, 
                                text=True)
            
            if proc.returncode == 0 and proc.stdout.strip():
                self.sudo_password = proc.stdout.strip()
                return True
            return False
            
        except Exception as e:
            messagebox.showerror("Error", 
                               "Failed to get administrator privileges.\n\n" + str(e))
            return False

    def run_with_sudo(self, cmd, **kwargs):
        """Run a command with sudo on macOS, using stored password"""
        if platform.system() != "Darwin":
            return subprocess.run(cmd, **kwargs)
            
        if not self.sudo_password and not self.get_sudo_password():
            raise Exception("Administrator privileges required")
            
        sudo_cmd = ['sudo', '-S'] + cmd
        kwargs['input'] = self.sudo_password + '\n'
        kwargs['text'] = True
        return subprocess.run(sudo_cmd, **kwargs)

if __name__ == "__main__":
    # Check for admin/root privileges on Linux only
    def is_admin():
        try:
            if platform.system() == "Windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            elif platform.system() == "Linux":
                return os.geteuid() == 0
            return True
        except:
            return False
    
    if platform.system() == "Linux" and not is_admin():
        print("This program requires administrator privileges to write to devices.")
        print("Please run it with sudo.")
        sys.exit(1)
    
    app = ISOFlasher()
    app.mainloop()
