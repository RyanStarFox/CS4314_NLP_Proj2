#!/bin/bash
# Smart Rebuild Script for Vulpis
# Integrates cleanup, python backend build, and tauri build

# Exit on error
set -e

echo "🚀 Starting Smart Build Process..."

# 1. Cleanup: Detach any stuck DMG volumes and kill old processes
echo "🧹 Step 1: Cleaning up environment..."
# Kill old backend processes if running
pkill -f "python-backend" || true
# Force detach any mounted DMGs from previous failed builds to avoid "Resource busy" errors
hdiutil info | grep "Vulpis" | grep "/dev/disk" | awk '{print $1}' | sort -u | xargs -n 1 hdiutil detach -force 2>/dev/null || true

# 2. Build Python Backend
echo "🐍 Step 2: Building Python Backend..."
# Ensure we are in the desktop-app directory
cd "$(dirname "$0")"

# Activate virtual env from parent directory
if [ -f "../.venv/bin/activate" ]; then
    source ../.venv/bin/activate
else
    echo "⚠️  Warning: Virtual environment not found in ../.venv"
fi

# Clean previous python builds
rm -rf dist build python-dist

# Build with PyInstaller
pyinstaller --clean --noconfirm python-backend.spec

# Organize output
if [ -d "dist/python-backend" ]; then
    mv dist/python-backend python-dist
    echo "✅ Python backend built explicitly."
else
    echo "❌ Python build failed: dist/python-backend not found."
    exit 1
fi

# 3. Build Tauri Frontend & Bundle
echo "🦀 Step 3: Building Tauri App..."
# Install dependencies just in case
npm install

# Build
npm run tauri build

echo "========================================"
echo "🎉 Build Success! Installer location:"
ls -lh src-tauri/target/release/bundle/dmg/*.dmg
echo "========================================"
