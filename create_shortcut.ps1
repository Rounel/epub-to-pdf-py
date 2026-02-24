# Cree un raccourci "EPUB to PDF" sur le Bureau de l'utilisateur courant

$exePath  = Join-Path $PSScriptRoot "dist\EPUB to PDF.exe"
$lnkPath  = Join-Path ([Environment]::GetFolderPath("Desktop")) "EPUB to PDF.lnk"

if (-not (Test-Path $exePath)) {
    Write-Error "Executable introuvable : $exePath`nLancez d'abord build.bat."
    exit 1
}

$shell    = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnkPath)

$shortcut.TargetPath       = $exePath
$shortcut.WorkingDirectory = Split-Path $exePath
$shortcut.Description      = "Convertir des fichiers EPUB en PDF"
$shortcut.WindowStyle      = 1   # Normal

# Utiliser l'icone integree a l'exe (index 0)
$shortcut.IconLocation = "$exePath,0"

$shortcut.Save()

Write-Host "Raccourci cree : $lnkPath"
