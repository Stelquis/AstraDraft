#!/bin/bash
# DeepAstraDraft API 服务启动脚本
set -e

echo "============================================"
echo "DeepAstraDraft API Server"
echo "============================================"
echo "Host: 0.0.0.0"
echo "Port: ${PORT:-8000}"
echo "Docs: http://localhost:${PORT:-8000}/docs"
echo "============================================"

cd /workspace
exec uvicorn backend.api:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --log-level info \
    --timeout-keep-alive 120
