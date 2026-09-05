# Start Streamlit app and automatically open browser
Write-Host "Starting Fusion Akhada app..." -ForegroundColor Green

# Start Streamlit in the background
$process = Start-Process -FilePath "python" -ArgumentList "-m", "streamlit", "run", "app.py" -PassThru -NoNewWindow

# Wait for the server to start (3 seconds)
Start-Sleep -Seconds 3

# Open the browser automatically
Start-Process "http://localhost:8501"

Write-Host "App started! Browser should open automatically." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the app." -ForegroundColor Yellow

# Keep the script running
Wait-Process -Id $process.Id