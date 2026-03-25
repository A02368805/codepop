#!/usr/bin/env bash
set -e

echo "Setting up CodePop development environment..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3.12 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Copy env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

# Run migrations
echo "Running migrations..."
cd server
../.venv/bin/python manage.py migrate

# Seed demo data
echo "Seeding demo data..."
../.venv/bin/python manage.py bootstrap_demo_data --reset

echo ""
echo "Setup complete! Start the server with:"
echo "  cd server && ../.venv/bin/python manage.py runserver 127.0.0.1:8000"
