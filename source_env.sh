#!/bin/bash
# Portable environment setup — works regardless of where the project is cloned.
# Usage: source source_env.sh  (must be sourced, not executed)

# Resolve the project root relative to this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ROS2
source /opt/ros/jazzy/setup.bash

# Workspace install
source "$SCRIPT_DIR/install/setup.bash"

# Expose venv packages to ROS2's Python
export PYTHONPATH="$SCRIPT_DIR/.venv/lib/python3.12/site-packages:$PYTHONPATH"

# eyeGestures is installed as a .pth (editable/source install) so we must
# add its actual source directory explicitly. Update this path if it moves.
EYEGESTURES_SRC="$(cat "$SCRIPT_DIR/.venv/lib/python3.12/site-packages/_eyegestures.pth" 2>/dev/null)"
if [ -n "$EYEGESTURES_SRC" ]; then
    export PYTHONPATH="$EYEGESTURES_SRC:$PYTHONPATH"
    echo "  eyeGestures  : $EYEGESTURES_SRC"
else
    echo "  WARNING: _eyegestures.pth not found or empty"
fi

echo "Environment ready."
echo "  Project root : $SCRIPT_DIR"
echo "  PYTHONPATH   : $PYTHONPATH"