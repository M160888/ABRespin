#!/bin/bash
# Horsebox Control System - Demo Startup Script
# Starts the Flask server for development/demo purposes

set -e

echo "🐴 Starting Horsebox Control System Demo..."
echo ""

# Check if we're in the right directory
if [ ! -d "horsebox-kiosk" ]; then
    echo "❌ Error: horsebox-kiosk directory not found"
    echo "Please run this script from the repository root"
    exit 1
fi

# Check Python dependencies
echo "📦 Checking dependencies..."
cd horsebox-kiosk

if ! python -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not found. Installing dependencies..."
    pip install -r requirements.txt
fi

echo "✅ Dependencies OK"
echo ""

# Start the Flask server
echo "🚀 Starting Flask server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🌐 Access the UI at:"
echo "     http://localhost:5000"
echo ""
echo "  ⚠️  Running in demo mode (Modbus hardware not required)"
echo ""
echo "  Press Ctrl+C to stop the server"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the Flask app
python src/api/app.py
