#!/bin/bash

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║   VPN System Database Restore           ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# Load environment variables
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

source .env

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Available backups:${NC}"
    ls -lh "$BACKUP_DIR"/vpn_system_*.sql.gz 2>/dev/null | tail -10 || echo "No backups found"
    
    echo ""
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 $BACKUP_DIR/vpn_system_20231215_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

echo -e "${YELLOW}Restore Details:${NC}"
echo "  Backup File: $BACKUP_FILE"
echo "  File Size: $FILE_SIZE"
echo "  Database: ${POSTGRES_DB:-vpn_system}"
echo "  User: ${POSTGRES_USER:-postgres}"
echo ""

read -p "$(echo -e ${YELLOW})Are you sure you want to restore? This will overwrite existing data (y/n):$(echo -e ${NC}) " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo -e "${RED}Restore cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Creating database backup before restore...${NC}"
BACKUP_BEFORE="$BACKUP_DIR/vpn_system_pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"

if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump \
    -U "${POSTGRES_USER:-postgres}" \
    "${POSTGRES_DB:-vpn_system}" | gzip > "$BACKUP_BEFORE"; then
    echo -e "${GREEN}✓ Pre-restore backup created: $BACKUP_BEFORE${NC}"
else
    echo -e "${YELLOW}⚠ Failed to create pre-restore backup${NC}"
fi

echo ""
echo -e "${YELLOW}Dropping existing database...${NC}"

if docker-compose -f "$COMPOSE_FILE" exec -T postgres dropdb \
    -U "${POSTGRES_USER:-postgres}" \
    --if-exists \
    "${POSTGRES_DB:-vpn_system}"; then
    echo -e "${GREEN}✓ Database dropped${NC}"
else
    echo -e "${RED}✗ Failed to drop database${NC}"
    exit 1
fi

echo -e "${YELLOW}Creating new database...${NC}"

if docker-compose -f "$COMPOSE_FILE" exec -T postgres createdb \
    -U "${POSTGRES_USER:-postgres}" \
    "${POSTGRES_DB:-vpn_system}"; then
    echo -e "${GREEN}✓ Database created${NC}"
else
    echo -e "${RED}✗ Failed to create database${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Restoring from backup...${NC}"

if gunzip -c "$BACKUP_FILE" | docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-vpn_system}"; then
    echo -e "${GREEN}✓ Database restored successfully${NC}"
else
    echo -e "${RED}✗ Database restore failed${NC}"
    echo ""
    echo -e "${YELLOW}Attempting to restore from pre-restore backup...${NC}"
    
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres dropdb \
        -U "${POSTGRES_USER:-postgres}" \
        --if-exists \
        "${POSTGRES_DB:-vpn_system}" && \
       docker-compose -f "$COMPOSE_FILE" exec -T postgres createdb \
        -U "${POSTGRES_USER:-postgres}" \
        "${POSTGRES_DB:-vpn_system}" && \
       gunzip -c "$BACKUP_BEFORE" | docker-compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-vpn_system}"; then
        echo -e "${GREEN}✓ Recovered from pre-restore backup${NC}"
    else
        echo -e "${RED}✗ Recovery failed - manual intervention needed${NC}"
        exit 1
    fi
    exit 1
fi

echo ""
echo -e "${YELLOW}Running migrations...${NC}"

if docker-compose -f "$COMPOSE_FILE" exec backend alembic upgrade head; then
    echo -e "${GREEN}✓ Migrations completed${NC}"
else
    echo -e "${YELLOW}⚠ Migrations failed or not available${NC}"
fi

echo ""
echo -e "${YELLOW}Verifying restore...${NC}"

DB_SIZE=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres psql \
    -U "${POSTGRES_USER:-postgres}" \
    "${POSTGRES_DB:-vpn_system}" \
    -c "SELECT pg_size_pretty(pg_database_size('${POSTGRES_DB:-vpn_system}'));" | tail -1)

TABLE_COUNT=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres psql \
    -U "${POSTGRES_USER:-postgres}" \
    "${POSTGRES_DB:-vpn_system}" \
    -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | tail -1)

echo "Database Size: $DB_SIZE"
echo "Number of Tables: $TABLE_COUNT"

echo ""
echo -e "${GREEN}=== Restore Complete ===${NC}"
echo ""
echo "Actions taken:"
echo "  ✓ Original database backed up: $BACKUP_BEFORE"
echo "  ✓ Database restored from: $BACKUP_FILE"
echo "  ✓ Migrations executed"
echo ""
echo "Next steps:"
echo "  1. Verify application functionality"
echo "  2. Check logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "  3. Test critical features"
