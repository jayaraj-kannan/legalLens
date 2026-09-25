#!/usr/bin/env bash
set -e

# Ensure Docker Desktop binaries are in PATH
export PATH="$HOME/.docker/bin:/usr/local/bin:$PATH"

# LegalLens - Docker Compose Launch Script
echo "======================================================"
echo "⚖️  LegalLens - Docker Compose Launcher"
echo "======================================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 1. Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "❌ Docker CLI not found. Please install Docker Desktop, OrbStack, or Colima."
    echo "   macOS Install: brew install --cask docker"
    exit 1
fi

# Check Docker daemon status
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running. Please start Docker."
    exit 1
fi

# 2. Check or create .env
if [ ! -f ".env" ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
fi

# 3. Locate GCP Credentials
ADC_PATH="${HOME}/.config/gcloud/application_default_credentials.json"
if [ -f "$ADC_PATH" ]; then
    echo "✅ Found Google Application Default Credentials at $ADC_PATH"
else
    echo "⚠️  No ADC file detected at $ADC_PATH."
    echo "   To authenticate Vertex AI and GCS, run:"
    echo "     gcloud auth application-default login"
fi

# 4. Build and start containers
echo "🚀 Building and starting LegalLens multi-container stack..."
docker compose up --build -d

echo ""
echo "⏳ Waiting for containers to become healthy..."
sleep 5

docker compose ps

echo ""
echo "======================================================"
echo "🎉 LegalLens Services are Online!"
echo "======================================================"
echo "  🖥️  Frontend UI:    http://localhost:3000"
echo "  ⚡ Backend API:     http://localhost:8080 (Docs: http://localhost:8080/docs)"
echo "  🤖 ADK Agent:       http://localhost:8000"
echo "======================================================"
echo "To view live logs:   docker compose logs -f"
echo "To stop stack:       docker compose down"
echo "======================================================"
