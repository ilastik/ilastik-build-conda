@echo OFF
SETLOCAL

rem find CPLEX in the original PATH. FIXME: do we need to be more specific, e.g. cplex125.dll ?
where /Q cplex
if NOT ERRORLEVEL 1 for /f "delims=" %%a in ('where cplex') do @set CPLEX_PATH=%%~dpa

rem find Gurobi in the original PATH. FIXME: do we need to be more specific, e.g. gurobi55.dll ?
where /Q gurobi
if NOT ERRORLEVEL 1 for /f "delims=" %%a in ('where gurobi') do @set GUROBI_PATH=%%~dpa

rem overwrite PATH with only what ilastik needs
set INSTALL_DIR=%~dp0
set PATH=%INSTALL_DIR%;%INSTALL_DIR%Library\bin;%INSTALL_DIR%DLLs

rem re-insert CPLEX and Gurobi into the PATH if they were found
rem (note: we cannot use 'if () else ()' here, because it conflicts with parentheses in the %PATH%)
if DEFINED CPLEX_PATH set PATH=%PATH%;%CPLEX_PATH%
if DEFINED GUROBI_PATH set PATH=%PATH%;%GUROBI_PATH%

rem set more paths
set QTDIR=%INSTALL_DIR%Library
IF ["%ILASTIK_DIR%"] EQU [""] set ILASTIK_DIR=ilastik
set PYTHONPATH=%ILASTIK_DIR%\volumina;%ILASTIK_DIR%
set PYTHONHOME=%INSTALL_DIR%
set PYTHONNOUSERSITE=1
set QT_PLUGIN_PATH=%QTDIR%\plugins

rem check if this script was called as 'lastik test' or 'ilastik python ...'
if /I "%1" EQU "test" goto :testing
if /I "%1" EQU "python" goto :python

rem if not, start ilastik normally
echo Loading ilastik from "%ILASTIK_DIR%"
"%INSTALL_DIR%python" "%ILASTIK_DIR%\ilastik\ilastik.py" %*
goto :end

rem ################################

:python

rem extract the command line args to be passed on to python
rem (the initial 'python' arg should be dropped)
set args=
:parse_args
IF "%~2"=="" GOTO end_parse_args
set args=%args% %2
SHIFT
GOTO parse_args
:end_parse_args

echo ----------------------------
echo Running python command...
"%INSTALL_DIR%python\python" %args%
goto :end

rem ################################

:testing

rem run selected tests
set failed=0

echo ----------------------------
echo Running volumina tests...
cd "%ILASTIK_DIR%\volumina"
"%INSTALL_DIR%python\python" -m pytest
if %errorlevel% neq 0 set failed=1

echo ----------------------------
echo Running ilastik and lazyflow tests...
cd "%ILASTIK_DIR%"
"%INSTALL_DIR%python\python" -m pytest --run-legacy-gui
if %errorlevel% neq 0 set failed=1

if %failed% NEQ 0 ENDLOCAL & exit /b 1

rem ################################

:end
ENDLOCAL
