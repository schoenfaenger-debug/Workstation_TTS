@echo off
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --onefile --windowed --name Workstation_TTS_v1 main.py
mkdir Workstation_TTS_v1 2>nul
copy dist\Workstation_TTS_v1.exe Workstation_TTS_v1\
powershell -NoProfile -Command "Compress-Archive -Force Workstation_TTS_v1 Workstation_TTS_v1.zip"
