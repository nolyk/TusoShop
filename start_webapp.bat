@echo off
setlocal
cd /d "%~dp0"
set "BASE_PYTHON=%LocalAppData%\Programs\Python\Python310\python.exe"
if not exist "%BASE_PYTHON%" set "BASE_PYTHON=py -3.10"
set "WEBAPP_PYTHON=%~dp0.webapp_venv\Scripts\python.exe"

echo Starting AutoShop Mini App on http://127.0.0.1:8080
if not exist "%WEBAPP_PYTHON%" (
  echo Preparing isolated Mini App environment...
  %BASE_PYTHON% -m venv --system-site-packages "%~dp0.webapp_venv"
  if errorlevel 1 goto failed
)

"%WEBAPP_PYTHON%" -m pip install --disable-pip-version-check --no-deps -r requirements-webapp.txt
if errorlevel 1 goto failed
"%WEBAPP_PYTHON%" web_main.py
if errorlevel 1 goto failed
goto end

:failed
echo Mini App failed to start. See the error above.

:end
pause
