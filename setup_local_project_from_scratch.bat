@echo off
rmdir /s /q .\venv

python -m pip install --upgrade pip
python -m pip install virtualenv
python -m virtualenv venv

@REM .\venv\Scripts\activate.bat
venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
