#!/bin/bash

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
FAILED=0

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║   VPN System Health Check               ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# Check Docker
echo -e "${YELLOW}Checking Docker...${NC}"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${GREEN}✓ Docker: $DOCKER_VERSION${NC}"
else
    echo -e "${RED}✗ Docker not found${NC}"
    FAILED=$((FAILED + 1))
fi

# Check Docker Compose
echo -e "${YELLOW}Checking Docker Compose...${NC}"
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    echo -e "${GREEN}✓ Docker Compose: $COMPOSE_VERSION${NC}"
else
    echo -e "${RED}✗ Docker Compose not found${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""
echo -e "${YELLOW}Checking Services...${NC}"

# Check PostgreSQL
echo -n "PostgreSQL: "
if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    FAILED=$((FAILED + 1))
fi

# Check Redis
echo -n "Redis: "
if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    FAILED=$((FAILED + 1))
fi

# Check Backend
echo -n "Backend: "
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    FAILED=$((FAILED + 1))
fi

# Check Admin Panel
echo -n "Admin Panel: "
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    FAILED=$((FAILED + 1))
fi

# Check Nginx
echo -n "Nginx: "
if curl -sf http://localhost:80 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""
echo -e "${YELLOW}Container Status:${NC}"
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo -e "${YELLOW}Disk Usage:${NC}"
df -h | grep -E "^/dev/|Filesystem"

echo ""
echo -e "${YELLOW}Memory Usage:${NC}"
free -h

echo ""
echo -e "${YELLOW}Docker Disk Usage:${NC}"
docker system df

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=== All health checks passed! ===${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}=== $FAILED health checks failed ===${NC}"
    exit 1
fi
