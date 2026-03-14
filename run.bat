@echo off
chcp 65001 >nul
echo WILLVI MOTORS VMS 시작 중...
cd /d "%~dp0"
"C:\Users\강승일\AppData\Local\Python\bin\python.exe" -m streamlit run app.py
pause
