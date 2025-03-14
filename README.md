# TablaRaza - ISO Flasher

TablaRaza is a cross-platform GUI application for flashing ISO images to USB drives and SD cards. This tool provides a simple and intuitive interface for creating bootable media. Does not require admin privileges on Windows!

## Features

- Cross-platform (Windows, macOS, Linux)
- Admin not required in windows for install or usage
- Format devices before flashing

## Download

Pre-built executables are available for download:

- [Windows](https://github.com/Nat-As/Tablaraza/releases/latest/download/TablaRaza-Windows.exe)
- [macOS](https://github.com/Nat-As/Tablaraza/releases/latest/download/TablaRaza-MacOS.dmg)
- [Linux](https://github.com/Nat-As/Tablaraza/releases/latest/download/TablaRaza-Linux)

## Usage

1. Download and run the appropriate executable for your platform
2. Browse and select your ISO file
3. Select the target device from the dropdown
4. Click "Flash ISO" and confirm
5. Wait for the flashing process to complete

![screenshot](doc/screenshot.png)

**Note:** On Linux and macOS, you may need to run the application with sudo/admin privileges.

## Building from Source

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/Nat-As/Tablaraza.git
   cd Tablaraza
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```

### Building executables manually

You can build executables manually using PyInstaller:

**Windows:**
```
pyinstaller --onefile --windowed --icon=resources/icon.ico --name=TablaRaza main.py
```

**macOS:**
```
pyinstaller --onefile --windowed --icon=resources/icon.icns --name=TablaRaza main.py
```

**Linux:**
```
pyinstaller --onefile --name=TablaRaza main.py
```

## License

[MIT](LICENSE)
