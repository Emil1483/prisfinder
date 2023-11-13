$currentDir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$pythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH")

if (-not $pythonPath) {
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $currentDir)
} elseif ($pythonPath -like "*" + $currentDir + "*") {
    Write-Host "PYTHONPATH already contains the current directory."
} else {
    $updatedPath = $pythonPath + ";" + $currentDir
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $updatedPath)
    Write-Host "Updated PYTHONPATH to include the current directory."
}