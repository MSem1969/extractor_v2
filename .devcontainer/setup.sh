#!/bin/bash
set -e

echo "=========================================="
echo "  TO_EXTRACTOR - Codespaces Setup"
echo "=========================================="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
sleep 3

# Start PostgreSQL if not running
sudo service postgresql start || true
sleep 2

# Create database and user
echo "Setting up database..."
sudo -u postgres psql -c "CREATE USER to_extractor_user WITH PASSWORD 'to_extractor_pwd';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE to_extractor OWNER to_extractor_user;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE to_extractor TO to_extractor_user;" 2>/dev/null || true

# Import database dump
echo "Importing database..."
if [ -f "database_export.dump" ]; then
    sudo -u postgres pg_restore -d to_extractor --clean --if-exists database_export.dump 2>/dev/null || \
    sudo -u postgres pg_restore -d to_extractor database_export.dump || true
    echo "Database imported successfully!"
else
    echo "Warning: database_export.dump not found"
fi

# Grant permissions
sudo -u postgres psql -d to_extractor -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO to_extractor_user;" 2>/dev/null || true
sudo -u postgres psql -d to_extractor -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO to_extractor_user;" 2>/dev/null || true

# Setup Backend
echo "Setting up backend..."
cd backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env for Codespaces
cat > .env << 'EOF'
DATABASE_URL=postgresql://to_extractor_user:to_extractor_pwd@localhost:5432/to_extractor
SECRET_KEY=dev-secret-key-for-codespaces
DEBUG=true
EOF

cd ..

# Setup Frontend
echo "Setting up frontend..."
cd frontend
npm install
cd ..

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "To start the application:"
echo ""
echo "  Backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0"
echo "  Frontend: cd frontend && npm run dev -- --host"
echo ""
echo "=========================================="
