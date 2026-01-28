#!/bin/bash
# =============================================================================
# STARTUP SCRIPT FOR DJANGO BACKEND
# =============================================================================

set -e

echo "=== Starting Mars Devs Backend ==="
echo ""

echo "Step 1: Running migrations..."
python manage.py migrate --noinput
echo "Migrations complete!"
echo ""

echo "Step 2: Running seed data..."
python manage.py seed || echo "Seed already exists or failed"
echo ""

echo "Step 3: Starting Gunicorn..."
exec gunicorn marsdevs.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
