#!/bin/sh
# Startup script for Render deployment

set -e

echo "🚀 Starting ShoktiAI Backend..."

# Run database migrations
echo "📊 Running database migrations..."
alembic upgrade head

# Start the application
echo "🌐 Starting Uvicorn server..."
exec uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}
