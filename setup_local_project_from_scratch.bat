@echo off
rmdir /s /q .\venv

python3 -m pip install --upgrade pip
python3 -m pip install virtualenv
python3 -m virtualenv venv

@REM .\venv\Scripts\activate.bat
venv\Scripts\Activate.ps1

python3 -m pip install -r requirements.txt
