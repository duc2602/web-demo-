@echo off
setlocal

rem Đợi ~8 giây cho backend nạp xong (torch nạp khá lâu) rồi mở cửa sổ app
for /f "tokens=1,* delims==" %%A in ('findstr /b "APP_PORT=" "%~dp0backend\.env"') do set "APP_PORT=%%B"
if not defined APP_PORT (
	echo APP_PORT is missing from backend\.env
	exit /b 1
)
set "APP_SCHEME=http"
for /f "tokens=1,* delims==" %%A in ('findstr /b "TLS_CERTFILE=" "%~dp0backend\.env"') do set "TLS_CERTFILE=%%B"
if defined TLS_CERTFILE set "APP_SCHEME=https"
start "" cmd /c "timeout /t 8 >nul & start msedge --app=%APP_SCHEME%://127.0.0.1:%APP_PORT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backend\start.ps1"