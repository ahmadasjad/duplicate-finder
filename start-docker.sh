#!/bin/bash

# Duplicate File Finder - Docker Setup Script
echo "🔍 Duplicate File Finder - Docker Setup"
echo "========================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker Compose is available"

# Build and start the application
echo ""
echo "🚀 Building and starting the Duplicate File Finder..."
echo "This may take a few minutes on the first run..."

# Stop any existing containers
docker-compose down 2>/dev/null

# Build and start the application
if docker-compose up --build; then
    echo ""
    echo "✅ Application started successfully!"
    echo "🌐 Open your browser and navigate to: http://localhost:8501"
else
    echo ""
    echo "❌ Failed to start the application. Please check the error messages above."
    echo ""
    echo "📋 Common troubleshooting steps:"
    echo "1. Make sure Docker Desktop is running"
    echo "2. Check if port 8501 is already in use"
    echo "3. Verify file permissions in the project directory"
    echo "4. Try running: docker-compose down && docker-compose up --build"
    exit 1
fi
