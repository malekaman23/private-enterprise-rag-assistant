# Frontend (React + Tailwind)

Ye naya, professional chat interface hai jo purane Streamlit app (`app.py`)
ki jagah leta hai. Iske chalne ke liye backend API (`api.py`) alag se
chalani padegi.

## Setup

```bash
cd frontend
npm install
```

## Chalane ka tareeka (2 terminals chahiye)

**Terminal 1 - Backend API:**
```bash
# personal-ai-assistant folder ke andar (frontend ke bahar)
venv312clean\Scripts\activate
uvicorn api:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Browser mein khulega: **http://localhost:5173**

## Production Build (final deployment ke liye)
```bash
npm run build
```
Isse `dist/` folder banega jisme final optimized files hongi.
