$currentDir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$pythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH", "User")

if (-not $pythonPath) {
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $currentDir, "User")
    Write-Host "Created PYTHONPATH environment variable with current directory."
} elseif ($pythonPath -like "*" + $currentDir + "*") {
    Write-Host "PYTHONPATH already contains the current directory."
} else {
    $updatedPath = $pythonPath + ";" + $currentDir
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $updatedPath, "User")
    Write-Host "Updated PYTHONPATH to include the current directory."
}