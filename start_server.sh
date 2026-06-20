#!/bin/bash
# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/backend"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "============================================"
echo "  ENIGMA AI — Traffic Violation Server"
echo "  Open browser at: http://127.0.0.1:8000"
echo "  Press Ctrl+C to stop"
echo "============================================"
python main.py
