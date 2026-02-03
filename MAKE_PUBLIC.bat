@echo off
echo ============================================================
echo DEPEX DASHBOARD - PUBLIC ACCESS SETUP
echo ============================================================
echo.
echo This will make your dashboard publicly accessible via ngrok
echo.
echo Step 1: Download ngrok from https://ngrok.com/download
echo Step 2: Place ngrok.exe in this folder
echo Step 3: Run this command: ngrok http 5000
echo.
echo After running ngrok, you'll get a public URL like:
echo https://abc123.ngrok.io
echo.
echo Share that URL with anyone to let them access your dashboard!
echo.
echo Press any key to open ngrok website...
pause
start https://ngrok.com/download
