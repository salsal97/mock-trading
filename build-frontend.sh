#!/bin/bash

echo "Building React frontend and integrating with Django..."

# Set production environment
export NODE_ENV=production

# Navigate to frontend directory and build
cd frontend

echo "Building React app for production..."
npm run build

if [ $? -ne 0 ]; then
    echo "ERROR: Frontend build failed"
    exit 1
fi

cd ..

# Create backend static directory if it doesn't exist
mkdir -p backend/static

# Remove old static files
rm -rf backend/static/*

# Copy React build files to Django static directory
echo "Copying React build files..."
cp -r frontend/build/* backend/static/

# Create index.html in templates directory for Django to serve
mkdir -p backend/templates
cp frontend/build/index.html backend/templates/

echo "Frontend build complete and integrated with Django!"
echo "React app will be served by Django at runtime" 