#!/bin/bash
# WebSocket Setup & Testing Guide

echo "🚀 Phase 2 Tier 7: WebSocket Real-time Updates - Quick Start"
echo "============================================================"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found"
    exit 1
fi

if ! command -v redis-cli &> /dev/null; then
    echo "⚠️  Redis CLI not found - make sure Redis is running"
fi

echo "✅ Prerequisites OK"
echo ""

# Start Redis (if not running)
echo "🔴 Starting Redis..."
if redis-cli ping &>/dev/null; then
    echo "✅ Redis is already running"
else
    echo "Starting Redis in background..."
    redis-server --daemonize yes --port 6379
    sleep 2
    if redis-cli ping &>/dev/null; then
        echo "✅ Redis started"
    else
        echo "❌ Failed to start Redis"
        exit 1
    fi
fi
echo ""

# Setup backend
echo "🐍 Setting up backend..."
cd backend || exit 1

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

echo "✅ Backend ready"
cd ..
echo ""

# Setup frontend
echo "📦 Setting up frontend..."
cd frontend || exit 1

if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install --silent
fi

echo "✅ Frontend ready"
cd ..
echo ""

# Display next steps
echo "🎯 Next Steps:"
echo "============="
echo ""
echo "1. Terminal 1 - Start Celery worker (for background tasks):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   celery -A app.celery_app worker -l info"
echo ""
echo "2. Terminal 2 - Start Celery Beat (for scheduled tasks):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   celery -A app.celery_app beat -l info"
echo ""
echo "3. Terminal 3 - Start FastAPI backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "4. Terminal 4 - Start frontend dev server:"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "5. Open browser:"
echo "   http://localhost:5173"
echo ""
echo "6. Test WebSocket progress:"
echo "   - Go to video upload page"
echo "   - Upload a video file"
echo "   - Watch real-time progress updates!"
echo ""
echo "📝 Testing WebSocket directly:"
echo "   python scripts/test_websocket_client.py --task-id <task_id>"
echo ""
echo "📚 Documentation:"
echo "   - Read: PHASE_2_TIER_7_IMPLEMENTATION.md"
echo "   - Read: PHASE_2_TIER_7_SUMMARY.md"
echo ""
echo "✅ Setup complete! 🎉"
