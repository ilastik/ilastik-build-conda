REM The git hash is prefixed with 'g' for some stupid reason.
git checkout %GIT_DESCRIBE_HASH:~1%
if errorlevel 1 exit 1
git submodule update --recursive
if errorlevel 1 exit 1

rem set version according to tag!
python ${RECIPE_DIR}/set_version.py %PREFIX%/ilastik/ilastik/__init__.py %PKG_VERSION%

REM Create .pyc files
python -m compileall ilastik
rem if errorlevel 1 exit 1

REM Add the ilastik modules to sys.path
copy "%RECIPE_DIR%\ilastik.pth.win" "%PREFIX%\Lib\site-packages\ilastik.pth"
if errorlevel 1 exit 1

REM Install the ilastik modules
xcopy /S ilastik "%PREFIX%\ilastik\ilastik\"
if errorlevel 1 exit 1
copy Readme* "%PREFIX%\ilastik-meta\"
if errorlevel 1 exit 1
