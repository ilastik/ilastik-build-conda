@if "%CONDA_ACTIVE_ENV%"=="" if NOT "%CONDA_DEFAULT_ENV%"=="" (
    set CONDA_ACTIVE_ENV=%CONDA_DEFAULT_ENV%
)

@if "%CONDA_ACTIVE_ENV%"=="" (
    echo 'ilastik-package' cannot be installed into the root environment.
    echo Use 'activate environment-name' to switch to another environment.
    exit 1
)

for /f %%i in (
    'python -c "import re;s = open('..\ilastik\ilastik\__init__.py').read();version_line = re.findall(r'__version_info__ *=.*', s)[0];exec(version_line);print('.'.join(map(str,__version_info__)))"'
) do set ILASTIK_PKG_VERSION=%%i

@echo "Building package for version %ILASTIK_PKG_VERSION%"

cd ../package

@rem copy the ilastik version as our package version
cat "ilastik.iss.in" ^
    | sed -e "s/@VERSION@/%ILASTIK_PKG_VERSION%/g" ^
    > "ilastik.iss"
