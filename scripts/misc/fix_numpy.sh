#!/bin/bash
# fix_numpy.sh - Quick fix for NumPy compatibility issues

echo "🔧 Fixing NumPy compatibility issues..."

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
    
    # Option 1: Downgrade NumPy to 1.x (recommended for ROS2)
    echo "📦 Downgrading NumPy to version 1.26.4 (compatible with ROS2)..."
    pip install "numpy<2.0" numpy==1.26.4
    
    # Reinstall opencv-python to ensure compatibility
    echo "📦 Reinstalling OpenCV for compatibility..."
    pip uninstall -y opencv-python opencv-contrib-python
    pip install opencv-python opencv-contrib-python
    
    echo "✅ NumPy fix complete!"
    echo "Current NumPy version:"
    python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
    
else
    echo "⚠️  No virtual environment detected."
    echo "Please activate your virtual environment and run this script again."
    echo "Or install system-wide (not recommended):"
    echo "  sudo pip install 'numpy<2.0'"
fi

echo ""
echo "🚀 Try launching again:"
echo "  ros2 launch system_coordinator test_system_launch.py"