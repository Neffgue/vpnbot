#!/bin/bash

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/vpn_system_$TIMESTAMP.sql.gz"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║   VPN System Database Backup            ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# Load environment variables
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

source .env

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo -e "${YELLOW}Starting backup...${NC}"
echo "Backup directory: $BACKUP_DIR"
echo "Database: ${POSTGRES_DB:-vpn_system}"
echo ""

# Backup PostgreSQL database
echo -e "${YELLOW}Dumping PostgreSQL database...${NC}"

if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump \
    -U "${POSTGRES_USER:-postgres}" \
    "${POSTGRES_DB:-vpn_system}" | gzip > "$BACKUP_FILE"; then
    
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Database backup successful${NC}"
    echo "Backup file: $BACKUP_FILE"
    echo "File size: $FILE_SIZE"
else
    echo -e "${RED}✗ Database backup failed${NC}"
    exit 1
fi

# Backup Redis data
echo -e "${YELLOW}Backing up Redis data...${NC}"
REDIS_BACKUP="$BACKUP_DIR/redis_$TIMESTAMP.rdb"

if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli BGSAVE > /dev/null 2>&1; then
    docker-compose -f "$COMPOSE_FILE" cp redis:/data/dump.rdb "$REDIS_BACKUP" 2>/dev/null || \
    echo -e "${YELLOW}⚠ Redis backup skipped (data in memory only)${NC}"
    
    if [ -f "$REDIS_BACKUP" ]; then
        echo -e "${GREEN}✓ Redis backup successful${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Redis backup skipped${NC}"
fi

# Create backup manifest
MANIFEST_FILE="$BACKUP_DIR/vpn_system_$TIMESTAMP.manifest"
cat > "$MANIFEST_FILE" << EOF
Backup Manifest
===============
Date: $(date)
Timestamp: $TIMESTAMP
Database: ${POSTGRES_DB:-vpn_system}
PostgreSQL Backup: $BACKUP_FILE
Redis Backup: $REDIS_BACKUP
Retention: $RETENTION_DAYS days

Restore Commands:
-----------------
# PostgreSQL:
gunzip -c $BACKUP_FILE | docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} ${POSTGRES_DB:-vpn_system}

# Redis:
docker-compose exec -T redis redis-cli shutdown
cat $REDIS_BACKUP > /path/to/redis/dump.rdb
docker-compose exec redis redis-server
EOF

echo -e "${GREEN}✓ Manifest created: $MANIFEST_FILE${NC}"

# Clean old backups
echo -e "${YELLOW}Cleaning old backups (older than $RETENTION_DAYS days)...${NC}"
DELETED_COUNT=0

find "$BACKUP_DIR" -type f -name "vpn_system_*.sql.gz" -mtime +"$RETENTION_DAYS" | while read -r old_backup; do
    rm -f "$old_backup"
    echo -e "${YELLOW}  Deleted: $(basename $old_backup)${NC}"
    ((DELETED_COUNT++))
done

# Optional: Upload to S3
if [ ! -z "$S3_BUCKET" ] && [ ! -z "$AWS_ACCESS_KEY_ID" ]; then
    echo -e "${YELLOW}Uploading backup to S3...${NC}"
    
    if command -v aws &> /dev/null; then
        if aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/backups/" && \
           aws s3 cp "$MANIFEST_FILE" "s3://$S3_BUCKET/backups/"; then
            echo -e "${GREEN}✓ S3 upload successful${NC}"
        else
            echo -e "${RED}✗ S3 upload failed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ AWS CLI not installed, skipping S3 upload${NC}"
    fi
else
    echo -e "${YELLOW}⚠ S3 configuration not found, skipping S3 upload${NC}"
fi

echo ""
echo -e "${GREEN}=== Backup Complete ===${NC}"
echo ""
echo "Backup Details:"
echo "  SQL Backup: $BACKUP_FILE"
echo "  File Size: $FILE_SIZE"
echo "  Manifest: $MANIFEST_FILE"
echo ""
echo "Available backups in $BACKUP_DIR:"
ls -lh "$BACKUP_DIR"/vpn_system_*.sql.gz 2>/dev/null | tail -5 || echo "  No backups found"
