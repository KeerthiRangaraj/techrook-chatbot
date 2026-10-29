@echo off
echo TechRook Policy Chatbot - Starting...

echo.
echo Starting backend...
cd backend
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt -q
start "TechRook Backend" python main.py
cd ..

timeout /t 4 /nobreak >nul

echo.
echo Starting frontend...
cd frontend
call npm install --silent
start "TechRook Frontend" npm run dev
cd ..

echo.
echo TechRook chatbot is running!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo.
echo Demo: alice@techrook.in / bob@techrook.in / carol@techrook.in  (password: pass123)
