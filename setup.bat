@echo off

REM Check if Python is installed
python --version
IF ERRORLEVEL 1 (
    echo Python not found. Installing Python...
    REM You can download and install Python from the official website or use other methods.
    REM For this example, I'll assume you have the installer and run it. Adjust as necessary.
    start /wait path_to_python_installer.exe
)

REM Check if pip is installed
pip --version
IF ERRORLEVEL 1 (
    echo pip not found. Installing pip...
    powershell -Command "Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile get-pip.py"
    python get-pip.py
)

REM Install dependencies from requirements.txt
pip install -r requirements.txt

REM Run the config generator script
call config.bat
