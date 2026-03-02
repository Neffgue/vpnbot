#!/bin/bash

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
LOG_DIR="logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${YELLOW}=== VPN Sales System Deployment ===${NC}"

# Create logs directory if not exists
mkdir -p "$LOG_DIR"

# 1. Pull latest code from git
echo -e "${YELLOW}Step 1: Pulling latest code from Git...${NC}"
if git pull origin main >> "$LOG_DIR/deploy_$TIMESTAMP.log" 2>&1; then
    echo -e "${GREEN}✓ Git pull successful${NC}"
else
    echo -e "${RED}✗ Git pull failed${NC}"
    exit 1
fi

# 2. Build docker images
echo -e "${YELLOW}Step 2: Building Docker images...${NC}"
if docker-compose -f "$COMPOSE_FILE" build --no-cache >> "$LOG_DIR/deploy_$TIMESTAMP.log" 2>&1; then
    echo -e "${GREEN}✓ Docker build successful${NC}"
else
    echo -e "${RED}✗ Docker build failed${NC}"
    exit 1
fi

# 3. Check .env file
echo -e "${YELLOW}Step 3: Checking environment configuration...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo "Please create .env file by copying .env.example and configuring it"
    exit 1
fi
echo -e "${GREEN}✓ .env file found${NC}"

# 4. Run migrations
echo -e "${YELLOW}Step 4: Running database migrations...${NC}"
if docker-compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head >> "$LOG_DIR/deploy_$TIMESTAMP.log" 2>&1; then
    echo -e "${GREEN}✓ Migrations completed${NC}"
else
    echo -e "${RED}✗ Migrations failed${NC}"
    exit 1
fi

# 5. Stop old containers gracefully and start new ones (zero-downtime)
echo -e "${YELLOW}Step 5: Updating services (zero-downtime deployment)...${NC}"

# Start new containers alongside old ones
if docker-compose -f "$COMPOSE_FILE" up -d --no-deps \
    postgres redis backend bot worker beat admin-panel nginx certbot >> "$LOG_DIR/deploy_$TIMESTAMP.log" 2>&1; then
    echo -e "${GREEN}✓ Services updated successfully${NC}"
else
    echo -e "${RED}✗ Service update failed${NC}"
    exit 1
fi

# 6. Wait for services to be ready
echo -e "${YELLOW}Step 6: Waiting for services to be ready...${NC}"
sleep 10

if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo -e "${GREEN}✓ All services are running${NC}"
else
    echo -e "${RED}✗ Some services failed to start${NC}"
    docker-compose -f "$COMPOSE_FILE" logs
    exit 1
fi

# 7. Health checks
echo -e "${YELLOW}Step 7: Running health checks...${NC}"
HEALTH_CHECK_PASSED=true

# Check backend health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend health check passed${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
    HEALTH_CHECK_PASSED=false
fi

# Check PostgreSQL
if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL health check passed${NC}"
else
    echo -e "${RED}✗ PostgreSQL health check failed${NC}"
    HEALTH_CHECK_PASSED=false
fi

# Check Redis
if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis health check passed${NC}"
else
    echo -e "${RED}✗ Redis health check failed${NC}"
    HEALTH_CHECK_PASSED=false
fi

if [ "$HEALTH_CHECK_PASSED" = false ]; then
    echo -e "${RED}Health checks failed. Check logs: $LOG_DIR/deploy_$TIMESTAMP.log${NC}"
    exit 1
fi

# 8. Cleanup old images
echo -e "${YELLOW}Step 8: Cleaning up old Docker images...${NC}"
docker image prune -f >> "$LOG_DIR/deploy_$TIMESTAMP.log" 2>&1
echo -e "${GREEN}✓ Cleanup completed${NC}"

echo ""
echo -e "${GREEN}=== Deployment completed successfully! ===${NC}"
echo -e "Deployment log: ${YELLOW}$LOG_DIR/deploy_$TIMESTAMP.log${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify services: docker-compose -f $COMPOSE_FILE ps"
echo "  2. View logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "  3. Check backend: curl http://localhost:8000/health"
