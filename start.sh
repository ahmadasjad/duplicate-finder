#!/bin/bash
# Startup script for Duplicate Finder Docker application

echo "🔍 Starting Duplicate Finder Application..."
echo "🐳 Building Docker containers..."

# Build and start the application
docker-compose up --build

echo "✅ Application is running at http://localhost:8501"
echo "📁 You can scan the following directories:"
echo "   - /app/debug/ (sample files)"
echo "   - /host_home/ (your home directory - read only)"
echo "   - /host_tmp/ (tmp directory - read only)"
echo ""
echo "⚠️  To stop the application, press Ctrl+C"
