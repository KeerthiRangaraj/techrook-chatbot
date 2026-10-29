#!/bin/bash
# TechRook Chatbot — Quick Start Script
# Usage: bash start.sh

echo "🏰 TechRook Policy Chatbot — Starting..."

# Start backend in background
echo ""
echo "▶ Starting backend..."
cd backend
source venv/bin/activate 2>/dev/null || python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -q
python main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
sleep 3

# Start frontend
echo ""
echo "▶ Starting frontend..."
cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ TechRook chatbot is running!"
echo "   Frontend → http://localhost:5173"
echo "   Backend  → http://localhost:8000"
echo "   API docs → http://localhost:8000/docs"
echo ""
echo "Demo accounts:"
echo "  alice@techrook.in  (L0 Trainee)    password: pass123"
echo "  bob@techrook.in    (L2A Employee)  password: pass123"
echo "  carol@techrook.in  (L3 Director)   password: pass123"
echo ""
echo "Press Ctrl+C to stop both servers."

wait $BACKEND_PID $FRONTEND_PID
