@echo off
cd /d "%~dp0"
set "NGROK_EXE=C:\ngrok\ngrok.exe"
if exist "%NGROK_EXE%" goto run
set "NGROK_EXE=ngrok"
:run
echo Forwarding https traffic to IPv4 upstream http://127.0.0.1:8080
"%NGROK_EXE%" http 127.0.0.1:8080
pause
