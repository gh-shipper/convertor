@echo off
"C:\Users\user\AppData\Local\Programs\Python\Python314\python.exe" -m pip install -r requirements.txt pyinstaller
"C:\Users\user\AppData\Local\Programs\Python\Python314\python.exe" -m PyInstaller --onefile --windowed --icon Tabimage.ico ascii_translator.py
pause
