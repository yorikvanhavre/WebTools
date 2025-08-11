#!/usr/bin/env bash
set -e

if [ ! -f ./FreeCAD.AppImage ]; then
    wget https://github.com/FreeCAD/FreeCAD/releases/download/weekly-2025.08.07/FreeCAD_weekly-2025.08.07-Linux-x86_64-py311.AppImage -O FreeCAD.AppImage
    chmod +x ./FreeCAD.AppImage
fi

./FreeCAD.AppImage -M `pwd` -r TestWebTools