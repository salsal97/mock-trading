#!/bin/bash

echo "🔍 Checking API URL in built frontend files..."

# Check if build directory exists
if [ ! -d "frontend/build" ]; then
    echo "❌ Frontend build directory not found. Run build first."
    exit 1
fi

# Check for localhost references in built files
echo "🔍 Searching for localhost references..."
if grep -r "localhost:8000" frontend/build/ 2>/dev/null; then
    echo "❌ Found localhost:8000 references in build files!"
    echo "🔧 This means NODE_ENV was not set to 'production' during build"
else
    echo "✅ No localhost:8000 references found in build files"
fi

# Check for Azure URL references
echo "🔍 Searching for Azure URL references..."
if grep -r "salonis-mock-trading-app.azurewebsites.net" frontend/build/ 2>/dev/null; then
    echo "✅ Found Azure URL references in build files"
else
    echo "❌ No Azure URL references found in build files"
fi

# Check the main JS file specifically
echo "🔍 Checking main JavaScript file..."
MAIN_JS=$(find frontend/build/static/js -name "main.*.js" | head -1)
if [ -f "$MAIN_JS" ]; then
    echo "📄 Main JS file: $MAIN_JS"
    if grep -q "localhost:8000" "$MAIN_JS"; then
        echo "❌ Main JS contains localhost:8000"
    else
        echo "✅ Main JS does not contain localhost:8000"
    fi
    
    if grep -q "salonis-mock-trading-app.azurewebsites.net" "$MAIN_JS"; then
        echo "✅ Main JS contains Azure URL"
    else
        echo "❌ Main JS does not contain Azure URL"
    fi
else
    echo "❌ Main JS file not found"
fi

echo "�� Check complete!" 