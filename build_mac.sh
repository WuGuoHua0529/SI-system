#!/bin/bash

echo "Finding CustomTkinter library path..."
CTK_PATH=$(./venv/bin/python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))")

echo "CustomTkinter path: $CTK_PATH"

echo "Building macOS application..."
./venv/bin/pyinstaller --noconfirm --windowed --name "SIS" \
    --icon "assets/app_icon.png" \
    --add-data "$CTK_PATH:customtkinter" \
    --add-data "assets:assets" \
    main.py

echo "Build complete! Check the 'dist' folder."
