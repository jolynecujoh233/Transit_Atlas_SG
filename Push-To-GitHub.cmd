@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =======================================================
echo   Transit Atlas - Deploy to GitHub (jolynecujoh233)
echo =======================================================
echo.

set "GIT_CMD=git"
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if exist "..\git_portable\cmd\git.exe" (
        set "GIT_CMD=..\git_portable\cmd\git.exe"
    ) else if exist "git_portable\cmd\git.exe" (
        set "GIT_CMD=git_portable\cmd\git.exe"
    ) else (
        echo [ERROR] Git is not found. Please install Git or contact support.
        pause
        exit /b 1
    )
)

echo Using Git: !GIT_CMD!
echo Remote origin:
!GIT_CMD! remote -v
echo.

echo Instructions:
echo 1. Ensure you have created the repository on GitHub:
echo    https://github.com/jolynecujoh233/Transit_Atlas_SG
echo 2. When prompted for credentials by GitHub:
echo    - Username: jolynecujoh233
echo    - Password: Your GitHub Personal Access Token (with repo permission)
echo.
set /p CONFIRM="Press ENTER to push to main branch (or Ctrl+C to cancel)... "

!GIT_CMD! push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo =======================================================
    echo  [SUCCESS] Code successfully pushed to GitHub!
    echo.
    echo  Next steps to enable your public URL:
    echo  1. Go to: https://github.com/jolynecujoh233/Transit_Atlas_SG/settings/pages
    echo  2. Under 'Build and deployment' -^> 'Branch':
    echo     Select 'main' and '/ (root)', then click Save.
    echo.
    echo  Within 1-2 minutes, your deliverables will be live at:
    echo  Project Homepage: https://jolynecujoh233.github.io/Transit_Atlas_SG/
    echo  Interactive Demo: https://jolynecujoh233.github.io/Transit_Atlas_SG/demo-site/
    echo =======================================================
) else (
    echo.
    echo [ERROR] Push failed.
    echo Please make sure https://github.com/jolynecujoh233/Transit_Atlas_SG exists and you entered a valid GitHub token.
)
echo.
pause
