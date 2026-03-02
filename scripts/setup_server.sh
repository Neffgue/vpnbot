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
echo "║   VPN System Server Setup               ║"
echo "║   Ubuntu 22.04 - Production Ready       ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Check Ubuntu version
if ! grep -q "22.04" /etc/os-release; then
    echo -e "${YELLOW}Warning: This script is optimized for Ubuntu 22.04${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${YELLOW}=== System Update ===${NC}"
apt-get update
apt-get upgrade -y

echo -e "${YELLOW}=== Installing Dependencies ===${NC}"
apt-get install -y \
    curl \
    wget \
    git \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-pip

echo -e "${YELLOW}=== Installing Docker ===${NC}"
# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker
systemctl enable docker
systemctl start docker

echo -e "${GREEN}✓ Docker installed successfully${NC}"

echo -e "${YELLOW}=== Installing Docker Compose ===${NC}"
# Install Docker Compose standalone
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

echo -e "${GREEN}✓ Docker Compose installed successfully${NC}"

echo -e "${YELLOW}=== Installing Certbot ===${NC}"
apt-get install -y certbot python3-certbot-nginx

echo -e "${YELLOW}=== Configuring Firewall ===${NC}"
apt-get install -y ufw

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
ufw --force enable

echo -e "${GREEN}✓ Firewall configured${NC}"

echo -e "${YELLOW}=== Setting Up Swap ===${NC}"
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo -e "${GREEN}✓ 4GB swap created${NC}"
else
    echo -e "${YELLOW}⚠ Swap file already exists${NC}"
fi

echo -e "${YELLOW}=== Configuring System Limits ===${NC}"
cat >> /etc/security/limits.conf << 'EOF'
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF

sysctl -w fs.file-max=2097152
echo "fs.file-max=2097152" >> /etc/sysctl.conf

echo -e "${YELLOW}=== Creating Application Directory ===${NC}"
APP_DIR="/opt/vpn-system"

if [ ! -d "$APP_DIR" ]; then
    mkdir -p "$APP_DIR"
    echo -e "${GREEN}✓ Application directory created: $APP_DIR${NC}"
fi

read -p "$(echo -e ${YELLOW})Clone repository? Enter git URL (or press Enter to skip):$(echo -e ${NC}) " REPO_URL

if [ ! -z "$REPO_URL" ]; then
    echo -e "${YELLOW}Cloning repository...${NC}"
    cd "$APP_DIR"
    git clone "$REPO_URL" . || echo -e "${YELLOW}⚠ Repository already cloned${NC}"
    echo -e "${GREEN}✓ Repository cloned${NC}"
else
    echo -e "${YELLOW}⚠ Repository cloning skipped${NC}"
fi

echo -e "${YELLOW}=== Setting Up Environment ===${NC}"

if [ -f "$APP_DIR/.env.example" ]; then
    if [ ! -f "$APP_DIR/.env" ]; then
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        echo -e "${GREEN}✓ .env file created from .env.example${NC}"
        echo -e "${RED}⚠ IMPORTANT: Edit $APP_DIR/.env with your configuration${NC}"
    else
        echo -e "${YELLOW}⚠ .env file already exists${NC}"
    fi
fi

echo -e "${YELLOW}=== Setting Up Certbot ===${NC}"
read -p "$(echo -e ${YELLOW})Enter your domain name:$(echo -e ${NC}) " DOMAIN_NAME
read -p "$(echo -e ${YELLOW})Enter your email for Let's Encrypt:$(echo -e ${NC}) " LETSENCRYPT_EMAIL

if [ ! -z "$DOMAIN_NAME" ] && [ ! -z "$LETSENCRYPT_EMAIL" ]; then
    mkdir -p "$APP_DIR/nginx/certs"
    mkdir -p "$APP_DIR/nginx/www"
    
    echo -e "${YELLOW}Creating initial SSL certificate...${NC}"
    certbot certonly --standalone \
        -d "$DOMAIN_NAME" \
        --non-interactive \
        --agree-tos \
        --email "$LETSENCRYPT_EMAIL" || echo -e "${YELLOW}⚠ SSL certificate creation skipped or failed${NC}"
    
    # Copy certificates to app directory
    if [ -d "/etc/letsencrypt/live/$DOMAIN_NAME" ]; then
        cp -r "/etc/letsencrypt/live/$DOMAIN_NAME" "$APP_DIR/nginx/certs/" || true
        echo -e "${GREEN}✓ SSL certificates configured${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Domain configuration skipped${NC}"
fi

echo -e "${YELLOW}=== Setting Up Systemd Service ===${NC}"

cat > /etc/systemd/system/vpn-system.service << 'EOF'
[Unit]
Description=VPN System Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/vpn-system
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vpn-system.service

echo -e "${GREEN}✓ Systemd service created${NC}"

echo -e "${YELLOW}=== Setting Up Log Rotation ===${NC}"

cat > /etc/logrotate.d/vpn-system << EOF
$APP_DIR/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0640 root root
    sharedscripts
}
EOF

echo -e "${GREEN}✓ Log rotation configured${NC}"

echo -e "${YELLOW}=== Setting Up Monitoring ===${NC}"

cat > /usr/local/bin/check-vpn-health.sh << 'EOF'
#!/bin/bash

API_URL="http://localhost:8000"
THRESHOLD=3
LOG_FILE="/var/log/vpn-system-health.log"

if ! curl -f "$API_URL/health" > /dev/null 2>&1; then
    echo "$(date): VPN API is down" >> "$LOG_FILE"
    systemctl restart vpn-system
fi
EOF

chmod +x /usr/local/bin/check-vpn-health.sh

# Add cron job for health checks
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/check-vpn-health.sh") | crontab -

echo -e "${GREEN}✓ Health check monitoring configured${NC}"

echo ""
echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║   Setup Complete!                       ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Edit configuration: ${YELLOW}nano $APP_DIR/.env${NC}"
echo "2. Start services: ${YELLOW}systemctl start vpn-system${NC}"
echo "3. View logs: ${YELLOW}docker-compose -f $APP_DIR/docker-compose.prod.yml logs -f${NC}"
echo "4. Check status: ${YELLOW}systemctl status vpn-system${NC}"
echo ""

echo -e "${YELLOW}System Information:${NC}"
echo "  OS: $(lsb_release -ds)"
echo "  Docker: $(docker --version)"
echo "  Docker Compose: $(docker-compose --version)"
echo "  Certbot: $(certbot --version)"
echo "  App Directory: $APP_DIR"
echo ""
