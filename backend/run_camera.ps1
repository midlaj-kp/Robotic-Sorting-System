# Real Camera Startup Script (PowerShell)
# Auto-detects and starts backend with real camera

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "    CONVOYER - REAL CAMERA MODE" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Disable mock mode
$env:MOCK_HARDWARE = "false"
Write-Host "Mock hardware: DISABLED" -ForegroundColor Yellow

# Check if camera index is already set
if ($env:CAMERA_INDEX) {
    Write-Host "Using camera index: $($env:CAMERA_INDEX)" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Detecting available cameras..." -ForegroundColor Cyan
    Write-Host ""
    
    python find_camera.py
    
    Write-Host ""
    Write-Host "Enter the camera index from above (default is 0):" -ForegroundColor Yellow
    $cameraIndex = Read-Host "Camera Index"
    
    if ([string]::IsNullOrWhiteSpace($cameraIndex)) {
        $cameraIndex = "0"
    }
    
    $env:CAMERA_INDEX = $cameraIndex
    Write-Host "Using camera index: $cameraIndex" -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting backend with real camera..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

python run.py
