@echo off
setlocal EnableExtensions
REM Syntax-check the SAGE Lint plugin and deploy it into Sublime Text's Packages folder.
REM
REM Usage:   install.bat
REM Env:     SUBLIME_PACKAGES  override the destination Packages directory
REM          PYTHON            python interpreter used for the syntax check (default: python)
REM
REM On first install it writes SageLint.sublime-settings with linter_cwd pre-filled to this
REM checkout; on later runs it leaves an existing settings file untouched so your edits stay.

set "script_dir=%~dp0"

REM repo_root = script_dir\..\..\.. as an absolute, forward-slash path (Python consumes it as
REM cwd, and the settings file is JSON, where backslashes would need escaping).
pushd "%script_dir%..\..\.."
set "repo_root=%CD%"
popd
set "repo_root=%repo_root:\=/%"

if not defined PYTHON set "PYTHON=python"
set "package_name=SageLint"

REM Destination: SUBLIME_PACKAGES if set, else the Sublime Text 4 default under %APPDATA%.
if defined SUBLIME_PACKAGES (
  set "packages_dir=%SUBLIME_PACKAGES%"
  goto :have_packages
)
if defined APPDATA (
  set "packages_dir=%APPDATA%\Sublime Text\Packages"
  goto :have_packages
)
echo error: cannot locate Sublime Packages folder; set SUBLIME_PACKAGES>&2
exit /b 1

:have_packages
set "dest=%packages_dir%\%package_name%"

echo Checking syntax...
"%PYTHON%" -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read()); print('ok')" "%script_dir%sage_lint.py"
if errorlevel 1 exit /b 1

echo Deploying to %dest%
if not exist "%dest%" mkdir "%dest%"
copy /y "%script_dir%sage_lint.py" "%dest%" >nul
copy /y "%script_dir%Default.sublime-commands" "%dest%" >nul
copy /y "%script_dir%Context.sublime-menu" "%dest%" >nul
copy /y "%script_dir%SageLint.sublime-syntax" "%dest%" >nul
copy /y "%script_dir%README.md" "%dest%" >nul
REM Pins the package to Sublime's Python 3.8 plugin host (the plugin uses f-strings etc.,
REM which the legacy 3.3 host rejects). Must ship with the package.
copy /y "%script_dir%.python-version" "%dest%" >nul
copy /y "%script_dir%*.sublime-keymap" "%dest%" >nul

set "settings=%dest%\SageLint.sublime-settings"
if exist "%settings%" (
  echo Kept existing %settings%
  goto :done
)

REM Fill linter_cwd with this checkout. Done in Python so the path needs no escaping; chr(34)
REM builds the JSON quotes so the command line itself carries no nested double quotes.
set "SRC=%script_dir%SageLint.sublime-settings"
set "DST=%settings%"
set "ROOT=%repo_root%"
"%PYTHON%" -c "import os; q=chr(34); src=open(os.environ['SRC'],encoding='utf-8').read(); old=q+'linter_cwd'+q+': '+q+q; new=q+'linter_cwd'+q+': '+q+os.environ['ROOT']+q; open(os.environ['DST'],'w',encoding='utf-8').write(src.replace(old,new))"
if errorlevel 1 exit /b 1
echo Wrote %settings% (linter_cwd -^> %repo_root%)

:done
echo Done. Sublime Text auto-reloads the plugin; restart it if it does not pick up.
endlocal
