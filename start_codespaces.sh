#!/bin/bash
# =============================================================================
# TO_EXTRACTOR - Avvio Codespaces
# =============================================================================

echo "=========================================="
echo "  TO_EXTRACTOR - Avvio Codespaces"
echo "=========================================="

# 1. Avvia PostgreSQL
echo "[1/3] Avvio PostgreSQL..."
sudo service postgresql start 2>/dev/null || pg_ctlcluster 15 main start 2>/dev/null || echo "PostgreSQL potrebbe essere già attivo"
sleep 2

# 2. Avvia Backend
echo "[2/3] Avvio Backend (in background)..."
cd /workspaces/extractor_v2/backend
source venv/bin/activate
nohup uvicorn app.main:app --reload --host 0.0.0.0 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
sleep 2

# 3. Avvia Frontend
echo "[3/3] Avvio Frontend (in background)..."
cd /workspaces/extractor_v2/frontend
nohup npm run dev -- --host > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
sleep 2

echo ""
echo "=========================================="
echo "  TO_EXTRACTOR Avviato!"
echo "=========================================="
echo ""
echo "  Backend:  http://localhost:8000  (PID: $BACKEND_PID)"
echo "  Frontend: http://localhost:5173  (PID: $FRONTEND_PID)"
echo ""
echo "  Log backend:  tail -f /tmp/backend.log"
echo "  Log frontend: tail -f /tmp/frontend.log"
echo ""
echo "  Fermare tutto: pkill -f uvicorn; pkill -f vite"
echo ""
echo "  Credenziali: admin / admin123"
echo "=========================================="
