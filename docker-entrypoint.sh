#!/usr/bin/env bash
set -e

APP_MODULE="application:app"
HOST="0.0.0.0"
PORT="5001"
WORKERS=${WORKERS:-4}
LOG_LEVEL=${LOG_LEVEL:-info}

case "$1" in
  fastapi)
    echo "🚀 Starting FastAPI server (production mode)..."
    exec uv run gunicorn "$APP_MODULE" \
      -k uvicorn.workers.UvicornWorker \
      -w "$WORKERS" \
      -b "$HOST:$PORT" \
      --log-level "$LOG_LEVEL"
    ;;
  celery)
    echo "🔄 Starting Celery worker..."
    exec uv run python start_celery.py
    ;;
  celery-beat)
    echo "⏰ Starting Celery beat..."
    exec uv run celery -A application.common.tasks.celery_task.celery_app beat --loglevel=info
    ;;
  bash)
    echo "🐚 Starting bash shell..."
    exec /bin/bash
    ;;
  *)
    echo "Usage: docker run [OPTIONS] <image> [fastapi|celery|celery-beat|bash]"
    echo ""
    echo "Commands:"
    echo "  fastapi       - Start FastAPI server (production)"
    echo "  celery        - Start Celery worker"
    echo "  celery-beat   - Start Celery beat scheduler"
    echo "  bash          - Start bash shell"
    exit 1
    ;;
esac
