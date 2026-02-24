@echo off
setlocal

echo ============================================================
echo  EPUB to PDF Converter -- Build EXE
echo ============================================================
echo.

:: Verifier que pyinstaller est installe
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installation de PyInstaller...
    pip install pyinstaller
)

:: Nettoyer les anciens builds
if exist dist\        rmdir /s /q dist
if exist build\       rmdir /s /q build
if exist "EPUB to PDF.spec" del /q "EPUB to PDF.spec"

echo [INFO] Compilation en cours...
echo.

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "EPUB to PDF" ^
    --collect-data customtkinter ^
    --collect-data xhtml2pdf ^
    --collect-data ebooklib ^
    --hidden-import PIL ^
    --hidden-import reportlab ^
    --hidden-import html5lib ^
    gui.py

if errorlevel 1 (
    echo.
    echo [ERREUR] La compilation a echoue. Voir les messages ci-dessus.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Succes ! Fichier genere :
echo  %CD%\dist\EPUB to PDF.exe
echo ============================================================
echo.

:: Proposer de creer un raccourci bureau
set /p SHORTCUT="Creer un raccourci sur le Bureau ? [O/n] : "
if /i "%SHORTCUT%"=="" set SHORTCUT=O
if /i "%SHORTCUT%"=="O" (
    powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
    echo [OK] Raccourci cree sur le Bureau.
)

echo.
pause
endlocal
