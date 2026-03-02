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
echo "║   VPN Server Addition Wizard            ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# Load environment variables
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

source .env

# Check API connectivity
API_URL="${WEBHOOK_URL%/api/webhook}"
if [ -z "$API_URL" ]; then
    API_URL="http://localhost:8000"
fi

echo -e "${YELLOW}Using API URL: $API_URL${NC}"
echo ""

# Collect server information
read -p "$(echo -e ${YELLOW})Enter server name (e.g., US-01):$(echo -e ${NC}) " SERVER_NAME
if [ -z "$SERVER_NAME" ]; then
    echo -e "${RED}Server name cannot be empty${NC}"
    exit 1
fi

read -p "$(echo -e ${YELLOW})Enter country emoji (e.g., 🇺🇸):$(echo -e ${NC}) " COUNTRY_EMOJI
if [ -z "$COUNTRY_EMOJI" ]; then
    echo -e "${RED}Country emoji cannot be empty${NC}"
    exit 1
fi

read -p "$(echo -e ${YELLOW})Enter country name (e.g., United States):$(echo -e ${NC}) " COUNTRY_NAME
if [ -z "$COUNTRY_NAME" ]; then
    echo -e "${RED}Country name cannot be empty${NC}"
    exit 1
fi

read -p "$(echo -e ${YELLOW})Enter server host/IP address:$(echo -e ${NC}) " SERVER_HOST
if [ -z "$SERVER_HOST" ]; then
    echo -e "${RED}Server host cannot be empty${NC}"
    exit 1
fi

read -p "$(echo -e ${YELLOW})Enter server port (default 443):$(echo -e ${NC}) " SERVER_PORT
SERVER_PORT=${SERVER_PORT:-443}

read -p "$(echo -e ${YELLOW})Enter panel URL (e.g., https://panel.example.com):$(echo -e ${NC}) " PANEL_URL
if [ -z "$PANEL_URL" ]; then
    echo -e "${RED}Panel URL cannot be empty${NC}"
    exit 1
fi

read -p "$(echo -e ${YELLOW})Enter panel username:$(echo -e ${NC}) " PANEL_USERNAME
if [ -z "$PANEL_USERNAME" ]; then
    echo -e "${RED}Panel username cannot be empty${NC}"
    exit 1
fi

read -sp "$(echo -e ${YELLOW})Enter panel password:$(echo -e ${NC}) " PANEL_PASSWORD
echo ""
if [ -z "$PANEL_PASSWORD" ]; then
    echo -e "${RED}Panel password cannot be empty${NC}"
    exit 1
fi

read -p "$(echo -e ${YELLOW})Enter inbound ID (default 1):$(echo -e ${NC}) " INBOUND_ID
INBOUND_ID=${INBOUND_ID:-1}

read -p "$(echo -e ${YELLOW})Bypass Russian IP? (y/n, default n):$(echo -e ${NC}) " BYPASS_RU
case "$BYPASS_RU" in
    [yY][eE][sS]|[yY])
        BYPASS_RU=true
        ;;
    *)
        BYPASS_RU=false
        ;;
esac

echo ""
echo -e "${YELLOW}=== Server Information ===${NC}"
echo "Name: $SERVER_NAME"
echo "Country: $COUNTRY_EMOJI $COUNTRY_NAME"
echo "Host: $SERVER_HOST:$SERVER_PORT"
echo "Panel URL: $PANEL_URL"
echo "Panel User: $PANEL_USERNAME"
echo "Inbound ID: $INBOUND_ID"
echo "Bypass RU: $BYPASS_RU"
echo ""

read -p "$(echo -e ${YELLOW})Is this information correct? (y/n):$(echo -e ${NC}) " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo -e "${RED}Operation cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Adding server...${NC}"

# Prepare JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
    "name": "$SERVER_NAME",
    "country_emoji": "$COUNTRY_EMOJI",
    "country_name": "$COUNTRY_NAME",
    "host": "$SERVER_HOST",
    "port": $SERVER_PORT,
    "panel_url": "$PANEL_URL",
    "panel_username": "$PANEL_USERNAME",
    "panel_password": "$PANEL_PASSWORD",
    "inbound_id": $INBOUND_ID,
    "bypass_ru": $BYPASS_RU
}
EOF
)

# Send request to API
RESPONSE=$(curl -s -X POST "$API_URL/api/servers/add" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_SECRET_KEY" \
    -d "$JSON_PAYLOAD")

# Check response
if echo "$RESPONSE" | grep -q '"id"'; then
    SERVER_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo -e "${GREEN}✓ Server added successfully!${NC}"
    echo -e "Server ID: ${BLUE}$SERVER_ID${NC}"
    echo ""
    echo -e "${GREEN}Response:${NC}"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
else
    echo -e "${RED}✗ Failed to add server${NC}"
    echo ""
    echo -e "${RED}Response:${NC}"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Server Addition Complete ===${NC}"
