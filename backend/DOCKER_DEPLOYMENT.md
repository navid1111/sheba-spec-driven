# Docker Deployment Guide - ShoktiAI Backend

## Quick Start (Development)

### 1. Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- OpenAI API key

### 2. Setup Environment

```bash
# Copy environment template
cp .env.docker .env

# Edit .env and add your credentials
nano .env  # or use any text editor
```

**Required variables:**
- `OPENAI_API_KEY` - Your OpenAI API key

### 3. Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Check service status
docker-compose ps
```

### 4. Verify Deployment

```bash
# Check health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs

# View Prometheus metrics
curl http://localhost:8000/metrics

# View Prometheus UI
open http://localhost:9090

# View Grafana dashboard (optional)
open http://localhost:3000  # Login: admin/admin
```

---

## Services Overview

### Backend API (Port 8000)
- **URL**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

### PostgreSQL Database (Port 5432)
- **Host**: localhost:5432
- **Database**: shoktiai
- **User**: shoktiai (configurable)

### Prometheus (Port 9090)
- **URL**: http://localhost:9090
- Scrapes metrics from backend every 30s

### Grafana (Port 3000) - Optional
- **URL**: http://localhost:3000
- **Login**: admin/admin (change in .env)

---

## Common Commands

### Start/Stop Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d backend

# Stop all services
docker-compose down

# Stop and remove volumes (careful - deletes data!)
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Database Operations

```bash
# Access PostgreSQL shell
docker-compose exec postgres psql -U shoktiai -d shoktiai

# Run migrations manually
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Description"

# Backup database
docker-compose exec postgres pg_dump -U shoktiai shoktiai > backup.sql

# Restore database
docker-compose exec -T postgres psql -U shoktiai shoktiai < backup.sql
```

### Rebuild & Update

```bash
# Rebuild after code changes
docker-compose build backend

# Rebuild without cache
docker-compose build --no-cache backend

# Pull latest images
docker-compose pull

# Restart specific service
docker-compose restart backend
```

---

## Production Deployment

### 1. Use Production Compose File

```bash
# Start with production overrides
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Production features:**
- 2 backend replicas for high availability
- Resource limits (CPU/memory)
- Nginx reverse proxy with SSL
- Enhanced logging configuration

### 2. Production Environment Variables

Edit `.env` for production:

```bash
# Use strong secrets
JWT_SECRET=<generate-secure-random-string>
POSTGRES_PASSWORD=<strong-password>

# Use real SMTP/Twilio for production
OTP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=<your-sid>
TWILIO_AUTH_TOKEN=<your-token>

SMTP_USER=<your-email>
SMTP_PASSWORD=<app-password>

# Production URLs
BASE_URL=https://api.sheba.xyz
DEEP_LINK_BASE_URL=https://app.sheba.xyz/book
```

### 3. SSL Configuration (Nginx)

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name api.sheba.xyz;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.sheba.xyz;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

Place SSL certificates in `./ssl/` directory.

---

## Monitoring & Observability

### Prometheus Metrics

View metrics at http://localhost:9090

**Key metrics to monitor:**
- `ai_messages_sent_total` - Messages sent by agent/channel
- `ai_messages_delivered_total` - Delivery success rate
- `user_events_total` - User interactions (opens, clicks, conversions)

### Grafana Dashboard

1. Access Grafana: http://localhost:3000
2. Login with admin/admin
3. Add Prometheus data source: http://prometheus:9090
4. Import dashboard or create custom panels

**Sample queries:**
```promql
# Messages sent per hour
rate(ai_messages_sent_total[1h])

# Open rate by channel
rate(user_events_total{event_type="notification_opened"}[1h]) 
/ rate(ai_messages_sent_total[1h])

# Conversion rate
rate(user_events_total{event_type="booking_created"}[1h]) 
/ rate(ai_messages_sent_total[1h])
```

---

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Database not ready - wait and restart
docker-compose restart backend

# 2. Missing environment variables
docker-compose config  # Validate configuration
```

### Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec backend python -c "from src.lib.db import engine; print(engine.connect())"

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d postgres
# Wait 10 seconds
docker-compose up -d backend
```

### Migration issues

```bash
# Check migration status
docker-compose exec backend alembic current

# Run migrations manually
docker-compose exec backend alembic upgrade head

# Rollback one migration
docker-compose exec backend alembic downgrade -1
```

### Performance issues

```bash
# Check resource usage
docker stats

# View backend memory/CPU
docker stats shoktiai-backend

# Scale backend replicas (production)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=3
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: |
          cd backend
          docker build -t shoktiai-backend:latest .
      
      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push shoktiai-backend:latest
      
      - name: Deploy to server
        run: |
          ssh user@server 'cd /app && docker-compose pull && docker-compose up -d'
```

---

## Backup & Recovery

### Automated Backups

```bash
# Add to crontab for daily backups
0 2 * * * docker-compose exec postgres pg_dump -U shoktiai shoktiai | gzip > /backups/shoktiai_$(date +\%Y\%m\%d).sql.gz
```

### Manual Backup

```bash
# Backup database
docker-compose exec postgres pg_dump -U shoktiai shoktiai > backup_$(date +%Y%m%d).sql

# Backup volumes
docker run --rm -v shoktiai_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data.tar.gz /data
```

### Restore

```bash
# Restore database
docker-compose exec -T postgres psql -U shoktiai shoktiai < backup_20251105.sql

# Restore volume
docker run --rm -v shoktiai_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_data.tar.gz -C /
```

---

## Security Best Practices

### 1. Use Secrets Management

Don't commit `.env` files. Use:
- Docker secrets (Swarm mode)
- Kubernetes secrets
- AWS Secrets Manager / Azure Key Vault

### 2. Update Images Regularly

```bash
# Pull latest base images
docker-compose pull

# Rebuild with latest dependencies
docker-compose build --no-cache
```

### 3. Run as Non-Root

The Dockerfile already creates a `shoktiai` user (UID 1000) - containers run as non-root by default.

### 4. Network Isolation

Services communicate via internal `shoktiai-network` bridge. Only expose necessary ports (8000, 5432 for dev).

### 5. Enable HTTPS in Production

Always use SSL/TLS in production with Nginx or a load balancer.

---

## Scaling & High Availability

### Horizontal Scaling

```bash
# Scale backend to 3 replicas
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=3

# Use load balancer (Nginx/Traefik) to distribute traffic
```

### Database Replication

For production, use:
- PostgreSQL streaming replication
- Managed database service (AWS RDS, Azure Database, Neon)

### Redis for Session State (Optional)

Add Redis for distributed caching:

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

---

## Resource Requirements

### Minimum (Development)

- CPU: 2 cores
- RAM: 4 GB
- Disk: 10 GB

### Recommended (Production)

- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB SSD

### Per Service

| Service    | CPU   | Memory | Disk    |
|------------|-------|--------|---------|
| Backend    | 0.5-1 | 512MB  | 1 GB    |
| PostgreSQL | 1-2   | 1-2 GB | 20-50GB |
| Prometheus | 0.5   | 512MB  | 10 GB   |
| Grafana    | 0.25  | 256MB  | 1 GB    |

---

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Validate config: `docker-compose config`
3. Review health: `curl http://localhost:8000/health`
4. Consult APPLICATION_GUIDE.md for app-specific details

---

**Last Updated**: November 5, 2025  
**Docker Version**: 24.0+  
**Compose Version**: 2.20+
