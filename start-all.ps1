$Path = $PSScriptRoot

Write-Host "Starting Backend..."
Start-Process PowerShell -ArgumentList "-NoExit -Command `"cd '$Path'; .\.venv\Scripts\Activate.ps1; bbt-api`""

Write-Host "Starting Frontend..."
Start-Process PowerShell -ArgumentList "-NoExit -Command `"cd '$Path\frontend'; npm run dev`""

Write-Host "All services started."
