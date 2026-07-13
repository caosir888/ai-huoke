#!/bin/bash
# AI获客 V1.0 一键部署脚本
# Usage: bash deploy.sh [prod|dev]

set -e

MODE=${1:-prod}

echo "=== AI获客 V1.0 部署 ==="
echo "模式: $MODE"
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "请先安装 Docker: https://docs.docker.com/get-docker/"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "请先安装 Docker Compose"; exit 1; }

# Build frontend
echo "[1/4] 构建前端..."
cd frontend
npm install --silent
npm run build
cd ..
echo "前端构建完成"

# Check .env
if [ ! -f backend/.env ]; then
    echo "[2/4] 创建默认 .env 配置文件..."
    cat > backend/.env << 'ENVEOF'
DATABASE_URL=postgresql+asyncpg://aihuoke:aihuoke_secret@postgres:5432/aihuoke
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
JWT_SECRET=change-me-in-production-please
DEEPSEEK_API_KEY=your_deepseek_api_key
TTS_API_KEY=your_tts_api_key
DEBUG=false
ENVEOF
    echo "已创建 backend/.env，请编辑填入真实 API KEY"
else
    echo "[2/4] .env 已存在，跳过"
fi

# Start services
echo "[3/4] 启动 Docker 服务..."
if [ "$MODE" = "dev" ]; then
    docker compose up -d postgres redis minio backend
else
    docker compose up -d
fi

# Wait for backend
echo "[4/4] 等待服务就绪..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo "后端服务就绪"
        break
    fi
    sleep 2
done

echo ""
echo "=== 部署完成 ==="
echo "前端: http://localhost"
echo "API:  http://localhost:8000"
echo "MinIO: http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo "下一步:"
echo "1. 编辑 backend/.env 填入真实的 DEEPSEEK_API_KEY 和 TTS_API_KEY"
echo "2. 访问 http://localhost 注册账号"
echo "3. 查看日志: docker compose logs -f backend"
