#!/bin/bash
# Double-click in Finder to install CrystalPilot: runs install-mac.sh in a Terminal window.
# (The first time, macOS may refuse to open it: right-click it and choose Open.)
cd "$(dirname "$0")" || exit 1
bash ./install-mac.sh "$@"
echo
read -r -p "Press Return to close this window. " _
