#!/bin/bash
# Production startup script for OEM Incident Intelligence System

echo "=========================================="
echo "OEM Incident Intelligence System"
echo "=========================================="
echo ""

# Set Python path
export PYTHONPATH=.

# Check Python version
echo "[*] Checking Python version..."
python3 --version

# Kill existing processes
echo "[*] Checking for existing processes..."
pkill -f "uvicorn app:app" 2>/dev/null && echo "[OK] Killed existing uvicorn process"

# Wait a moment
sleep 2

# Start server
echo ""
echo "[*] Starting uvicorn server..."
echo "[*] Command: python3 -m uvicorn app:app --host 192.168.0.164 --port 4540"
echo ""

python3 -m uvicorn app:app --host 192.168.0.164 --port 4540

# If we get here, server stopped
echo ""
echo "[!] Server stopped"
