@echo off
rem =============================================================
rem  DirTreeEx.bat – dump a directory tree (incl. files) to .txt
rem  Usage  : double-click  OR  DirTreeEx  [rootFolder] [outFile]
rem  Author : koenfrontatie - koenvdwaal@gmail.com
rem =============================================================

setlocal EnableDelayedExpansion

:: ---------- CONFIG ---------------------------------------------
set "ROOT=%~1"
if "%ROOT%"=="" set "ROOT=%CD%"

set "OUT=%~2"
if "%OUT%"=="" set "OUT=tree_output.txt"

set "SKIPDIRS=node_modules .git dist build .vs venv logs storage __pycache__ trash-bin"
set "SKIPFILES=%~nx0 %OUT%"
:: ---------------------------------------------------------------

echo(
echo Generating tree for: "%ROOT%"
echo Writing report to  : "%OUT%"
echo Skipping folders   : %SKIPDIRS%
echo Skipping files     : %SKIPFILES%
echo --------------------------------------------------------------

> "%OUT%" (
    echo Directory tree of "%ROOT%"  ^|  Generated %DATE% %TIME%
    echo ============================================================
)

:: root line
for %%R in ("%ROOT%") do >> "%OUT%" echo %%~nxR

:: start the walk
call :walk "%ROOT%" ""
echo(
echo Done!  Report saved as "%OUT%"
pause
exit /b


:: ================================================================
:walk   %1 = current folder    %2 = current indent prefix
:: everything inside is “local” to this recursion level
setlocal EnableDelayedExpansion
set "CUR=%~1"
set "PAD=%~2"

:: ----- files first ----------------------------------------------
for %%F in ("!CUR!\*") do (
    if not exist "%%F\" (
        set "SKIP=0"
        for %%X in (%SKIPFILES%) do if /I "%%~nxF"=="%%X" set "SKIP=1"
        if !SKIP! EQU 0 >> "%OUT%" echo !PAD!^|   %%~nxF
    )
)

:: ----- then sub-folders -----------------------------------------
for /d %%D in ("!CUR!\*") do (
    set "SKIP=0"
    for %%X in (%SKIPDIRS%) do if /I "%%~nxD"=="%%X" set "SKIP=1"
    if !SKIP! EQU 0 (
        >> "%OUT%" echo !PAD!+--- %%~nxD
        call :walk "%%~fD" "!PAD!|   "
    )
)

endlocal
exit /b
