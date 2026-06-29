# Kon-Tiki Biochar dMRV FastAPI Microservice

A production-ready FastAPI microservice for receiving and processing digital Monitoring, Reporting, and Verification (dMRV) payloads from Flutter mobile applications tracking biochar production.

## Features

- **Idempotent API endpoints** with retry safety
- **PostgreSQL async database** with SQLAlchemy 2.0
- **Pydantic V2 validation** with strict schema enforcement
- **Media file uploads** with SHA-256 integrity verification
- **LCA carbon credit calculation** engine
- **Comprehensive test suite** with pytest-asyncio
- **Production-ready** with CORS, logging, and error handling

## Architecture

```
backend/
├── server.py           # FastAPI application with endpoints
├── models.py           # SQLAlchemy database models
├── db.py               # Database configuration and session management
├── lca_engine.py       # Life Cycle Assessment carbon credit calculator
├── requirements.txt    # Python dependencies
├── .env                # Environment configuration
└── tests/
    ├── test_api.py     # API endpoint tests
    └── test_lca_engine.py  # LCA calculation unit tests
```

## API Endpoints

### Health Check
```http
GET /api/health
```
Returns service status and timestamp.

### Batch Payload Submission
```http
POST /api/v1/batches
Headers:
  X-Idempotency-Key: {operation_id}
  Content-Type: application/json

Body:
{
  "batch_uuid": "uuid",
  "feedstock_species": "Lantana_camara",
  "harvest_timestamp": "2026-01-15T08:30:00Z",
  "moisture_percent": 12.5,
  "photo_path": "/sandbox/evidence/test.jpg",
  "sha256_hash": "64-char-hex-string",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "harvest_uptime_seconds": 3600
}
```

**Response (201 Created):**
```json
{
  "batch_uuid": "...",
  "operation_id": "...",
  "status": "RECEIVED",
  "duplicate": false,
  "received_at": "2026-01-15T08:30:00Z",
  "net_credit_t_co2e": 0.0255
}
```

**Idempotency:** Subsequent requests with the same `X-Idempotency-Key` return the original response with `duplicate: true`.

### Media Upload
```http
POST /api/v1/media
Headers:
  X-Idempotency-Key: {operation_id}
  X-Declared-SHA256: {expected_hash}
  Content-Type: multipart/form-data

Body:
  file: <binary_file>
```

**Response (200 OK):**
```json
{
  "server_sha256": "calculated_hash",
  "stored": true,
  "file_path": "/app/backend/uploads/..."
}
```

**Error (422 Unprocessable Entity):**
- If calculated SHA-256 doesn't match `X-Declared-SHA256`
- Response: `{"detail": "sha256_mismatch"}`

## LCA Engine

The `lca_engine.py` module calculates net carbon credits using biochar dMRV methodology:

**Formula:**
```
Net CO2e = (Feedstock mass × Yield × Carbon content × Stability) − Emissions
```

**Feedstock Species Supported:**
- Lantana_camara
- Wood_chips
- Agricultural_waste
- Default (fallback)

**Calculation Parameters:**
- Carbon content: 42-50% by dry weight
- Biochar yield: 20-30%
- Stability factor: 80-90% (permanence over 100 years)
- Process emissions: 8% of feedstock weight
- CO2e conversion: 1 tonne C = 3.667 tonnes CO2e

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 15+

### Setup

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dmrv
```

3. **Start PostgreSQL:**
```bash
sudo service postgresql start
```

4. **Create database:**
```bash
sudo -u postgres psql -c "CREATE DATABASE dmrv;"
```

5. **Run migrations:**
Database tables are auto-created on startup via SQLAlchemy `create_all()`.

## Running the Server

### Development
```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

### Production
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --workers 4
```

API docs available at: `http://localhost:8001/api/docs`

## Testing

### Run all tests:
```bash
pytest tests/ -v
```

### Run specific test suites:
```bash
# API endpoint tests
pytest tests/test_api.py -v

# LCA engine tests
pytest tests/test_lca_engine.py -v
```

### Test Coverage:
- ✅ Valid batch payload → 201
- ✅ Duplicate idempotency key → 200 (no duplicate insert)
- ✅ Malformed payload (missing sha256_hash) → 422
- ✅ Media upload with correct hash → 200 + server_sha256 matches
- ✅ Media upload with wrong declared hash → 422
- ✅ Extra fields forbidden → 422
- ✅ Invalid moisture_percent → 422
- ✅ Missing X-Idempotency-Key → 422
- ✅ LCA calculations for all feedstock species
- ✅ Moisture adjustment calculations
- ✅ Carbon sequestration calculations

## Database Schema

### Batches Table
```sql
CREATE TABLE batches (
    id SERIAL PRIMARY KEY,
    batch_uuid UUID UNIQUE NOT NULL,
    operation_id VARCHAR(255) UNIQUE NOT NULL,
    feedstock_species VARCHAR(255) NOT NULL,
    harvest_timestamp TIMESTAMPTZ NOT NULL,
    moisture_percent FLOAT NOT NULL,
    photo_path TEXT,
    sha256_hash VARCHAR(64) NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    harvest_uptime_seconds INT,
    status VARCHAR(32) DEFAULT 'RECEIVED',
    net_credit_t_co2e FLOAT DEFAULT 0.0,
    received_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Media Files Table
```sql
CREATE TABLE media_files (
    id SERIAL PRIMARY KEY,
    operation_id VARCHAR(255) UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL,
    filename VARCHAR(255),
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Error Handling

**422 Unprocessable Entity:**
- Missing required fields
- Invalid field values (e.g., moisture_percent > 100)
- Extra fields in payload (strict validation)
- SHA-256 hash mismatch

**400 Bad Request:**
- Missing or empty X-Idempotency-Key header

**500 Internal Server Error:**
- Database connection failures
- Unexpected server errors

## Production Considerations

1. **Environment Variables:**
   - Use `.env` for local development
   - Use environment variables or secrets manager in production

2. **Database:**
   - Enable connection pooling
   - Set up regular backups
   - Monitor query performance

3. **File Storage:**
   - Currently stores files locally in `/app/backend/uploads/`
   - For production, consider:
     - S3-compatible object storage
     - CDN for media delivery
     - Periodic cleanup of old files

4. **Logging:**
   - Logs to stdout (container-friendly)
   - Consider structured logging (JSON) for production
   - Integrate with log aggregation (ELK, CloudWatch, etc.)

5. **Monitoring:**
   - Set up health check monitoring
   - Track API response times
   - Monitor database connections
   - Alert on error rates

6. **Security:**
   - Enable HTTPS in production
   - Implement rate limiting
   - Add authentication/authorization
   - Validate file types and sizes for media uploads
   - Scan uploaded files for malware

## Integration with Flutter

The Flutter app should:

1. Generate a unique `operation_id` (UUID v4) for each request
2. Include `X-Idempotency-Key: {operation_id}` header
3. Calculate SHA-256 of files before upload
4. Include `X-Declared-SHA256` header for media uploads
5. Implement exponential backoff retry logic
6. Handle 422 errors by fixing payload and retrying with new operation_id

## License

MIT License

## Support

For issues or questions, please open an issue on the repository.
