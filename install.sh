#!/bin/bash
echo "======================================================="
echo "Installing dependecencies... "
echo "======================================================="

python3 -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "..."
echo "Installing complete!"