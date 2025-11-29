@echo off
echo Running Django migrations...
echo.

REM Activate virtual environment
call ..\..\venv\Scripts\activate.bat

REM Run migrations
python manage.py migrate

echo.
echo Migrations complete!
pause
