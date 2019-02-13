#!/bin/bash

echo "QualCoder will be copied to the directory /usr/share/"
echo "These actions require owner (sudo) permission"
echo "The installer will also try to install pyqt5 and lxml"
sudo cp -r QualCoder /usr/share/QualCoder
sudo cp QualCoder/GUI/QualCoder.png /usr/share/pixmaps/QualCoder.png
sudo cp QualCoder.desktop /usr/share/applications/QualCoder.desktop
sudo apt-get install python3-pyqt5
sudo apt-get install python3-lxml
echo "Installation completed."
echo "To remove QualCoder from Linux run the following in the terminal:"
echo "sudo rm -R /usr/share/QualCoder"
echo "sudo rm /usr/share/pixmaps/QualCoder.png"
