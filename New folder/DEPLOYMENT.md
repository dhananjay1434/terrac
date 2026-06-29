# Kon-Tiki dMRV Microservice - Deployment Guide

## Overview

This FastAPI microservice is designed to receive biochar dMRV payloads from Flutter mobile applications and calculate carbon credits using an LCA engine.

## Deployment Options

### 1. Docker Deployment (Recommended)

#### Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ .

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### Docker Compose
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: dmrv
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  api:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/dmrv
    depends_on:
      - postgres
    ports:
      - "8001:8001"
    volumes:
      - ./uploads:/app/uploads

volumes:
  postgres_data:
```

#### Run
```bash
docker-compose up -d
```

### 2. Kubernetes Deployment

#### deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dmrv-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dmrv-api
  template:
    metadata:
      labels:
        app: dmrv-api
    spec:
      containers:
      - name: api
        image: your-registry/dmrv-api:latest
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: dmrv-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: dmrv-api
spec:
  selector:
    app: dmrv-api
  ports:
  - port: 80
    targetPort: 8001
  type: LoadBalancer
```

### 3. Cloud Deployment

#### AWS (Elastic Beanstalk)
1. Create `Procfile`:
```
web: uvicorn server:app --host 0.0.0.0 --port 8001
```

2. Deploy:
```bash
eb init -p python-3.11 dmrv-api
eb create dmrv-production
eb deploy
```

#### Google Cloud Run
```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/dmrv-api

# Deploy
gcloud run deploy dmrv-api \
  --image gcr.io/PROJECT_ID/dmrv-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=postgresql+asyncpg://...
```

#### Heroku
```bash
heroku create dmrv-api
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

## Database Setup

### PostgreSQL Production Configuration

```sql
-- Create database
CREATE DATABASE dmrv;

-- Create user
CREATE USER dmrv_user WITH PASSWORD 'secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE dmrv TO dmrv_user;

-- Create indexes for performance
CREATE INDEX idx_batches_operation_id ON batches(operation_id);
CREATE INDEX idx_batches_batch_uuid ON batches(batch_uuid);
CREATE INDEX idx_batches_received_at ON batches(received_at);
CREATE INDEX idx_media_operation_id ON media_files(operation_id);
```

### Backup Strategy

```bash
# Daily backups
0 2 * * * pg_dump -U postgres dmrv > /backups/dmrv_$(date +\%Y\%m\%d).sql

# Restore
psql -U postgres dmrv < /backups/dmrv_20260115.sql
```

## Environment Variables

### Required
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dmrv
```

### Optional
```bash
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
MAX_UPLOAD_SIZE=10485760  # 10MB in bytes
```

## Monitoring

### Health Check
```bash
curl http://your-domain/api/health
```

### Prometheus Metrics (Optional)
Add to `server.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

### Logging
Logs are written to stdout. Configure log aggregation:
- AWS CloudWatch
- Google Cloud Logging
- ELK Stack
- Datadog

## Security Checklist

- [ ] Enable HTTPS/TLS
- [ ] Implement rate limiting
- [ ] Add authentication (API keys, JWT, OAuth)
- [ ] Validate file types and sizes
- [ ] Scan uploaded files for malware
- [ ] Use secrets manager for credentials
- [ ] Enable CORS with specific origins
- [ ] Implement request signing for Flutter app
- [ ] Set up WAF (Web Application Firewall)
- [ ] Regular security updates

## Performance Tuning

### Database Connection Pool
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
```

### Worker Configuration
```bash
# Production
uvicorn server:app \
  --host 0.0.0.0 \
  --port 8001 \
  --workers 4 \
  --loop uvloop \
  --http httptools
```

## Scaling Considerations

1. **Horizontal Scaling:**
   - Deploy multiple API instances behind a load balancer
   - Use Kubernetes HPA for auto-scaling

2. **Database Scaling:**
   - Use read replicas for queries
   - Implement connection pooling
   - Consider managed PostgreSQL services (RDS, Cloud SQL)

3. **File Storage:**
   - Use object storage (S3, GCS) instead of local filesystem
   - Implement CDN for media delivery

4. **Caching:**
   - Add Redis for frequently accessed data
   - Cache LCA calculations for common scenarios

## Disaster Recovery

1. **Database Backups:**
   - Automated daily backups
   - Point-in-time recovery
   - Cross-region replication

2. **Application:**
   - Blue-green deployments
   - Rollback procedures
   - Infrastructure as Code (Terraform)

## Cost Optimization

1. **Compute:**
   - Right-size instances based on load
   - Use spot instances for non-critical workloads
   - Implement auto-scaling

2. **Storage:**
   - Lifecycle policies for old files
   - Compress media files
   - Archive old batches

3. **Database:**
   - Optimize queries with indexes
   - Archive historical data
   - Use appropriate instance size

## Troubleshooting

### Common Issues

1. **Database Connection Errors:**
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Test connection
psql -U postgres -d dmrv -c "SELECT 1;"

# Check connection string
echo $DATABASE_URL
```

2. **Upload Directory Permissions:**
```bash
mkdir -p /app/backend/uploads
chmod 755 /app/backend/uploads
```

3. **Memory Issues:**
```bash
# Monitor memory
htop

# Increase worker processes or instance size
```

## Support

For deployment assistance, contact the development team or open an issue.
