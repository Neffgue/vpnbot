# Simple nginx stage — frontend is pre-built locally via:
#   cd admin-panel && npm ci && npm run build
# Then run: docker compose up -d --build
FROM nginx:1.25-alpine

# Copy pre-built dist folder (must exist before docker build)
COPY dist/ /usr/share/nginx/html/

# Remove default nginx config — our config is mounted via docker-compose volumes
RUN rm -f /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
