#!/bin/sh
set -e

python3 -m pip install --user pipx --quiet
python3 -m pipx ensurepath

export PATH="$HOME/.local/bin:$PATH"

echo "Installing..."
pipx install -e . --force --quiet

source ~/.bashrc

echo ""
echo "Done. Run: gizmo"
