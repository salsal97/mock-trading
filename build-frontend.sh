#!/bin/bash

echo "🏗️ Building React frontend and integrating with Django..."

# Navigate to frontend and build
echo "📦 Installing frontend dependencies..."
cd frontend
npm ci --production

echo "⚛️ Building React app for production..."
# Set NODE_ENV=production explicitly for the build
NODE_ENV=production npm run build

# Go back to root
cd ..

echo "📁 Preparing Django static files..."

# Create necessary directories
mkdir -p backend/static
mkdir -p backend/templates
mkdir -p backend/staticfiles

# Clean previous builds
rm -rf backend/static/*
rm -rf backend/templates/index.html

# Copy React build to Django static files
echo "📋 Copying React build files..."
cp -r frontend/build/static/* backend/static/ 2>/dev/null || echo "No static subdirectory found"
cp frontend/build/index.html backend/templates/
cp -r frontend/build/* backend/staticfiles/ 2>/dev/null || echo "Backup copy complete"

# Copy additional React files (manifest, favicon, etc.)
cp frontend/build/manifest.json backend/static/ 2>/dev/null || echo "No manifest.json found"
cp frontend/build/favicon.ico backend/static/ 2>/dev/null || echo "No favicon.ico found"

echo "✅ Frontend build complete and integrated with Django!"
echo "🎯 React app will be served by Django at runtime" 