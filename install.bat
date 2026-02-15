@echo off
echo =======================================================
echo Installing dependencies... 
echo =======================================================

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo ...
echo Installing complete!
pause 
