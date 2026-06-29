# Kon-Tiki Biochar dMRV System

## Project Overview

Complete FastAPI microservice implementation for Kon-Tiki biochar digital Monitoring, Reporting, and Verification (dMRV) system. This backend receives payloads from Flutter mobile applications and processes biochar production data with carbon credit calculations.

## 🎯 Features Implemented

✅ **Step 1: FastAPI + PostgreSQL Setup**
- SQLAlchemy async with PostgreSQL (asyncpg driver)
- Alembic-ready migration structure
- Production-ready database models

✅ **Step 2: Strict Pydantic V2 BatchPayload Model**
- All required fields validated
- Proper constraints (ge, le, min_length, max_length)
- Returns 422 for malformed payloads
- `extra="forbid"` for strict schema enforcement

✅ **Step 3: POST /api/v1/batches Endpoint**
- Idempotency via `X-Idempotency-Key` header
- PostgreSQL-backed duplicate detection
- Returns 201 on first insert, 200 on duplicate
- Race condition handling with IntegrityError recovery

✅ **Step 4: POST /api/v1/media Endpoint**
- Multipart file upload support
- SHA-256 hash verification
- Returns 422 with `sha256_mismatch` on hash mismatch
- Idempotent file storage

✅ **Step 5: Comprehensive pytest Test Suite**
- ✅ Test 1: Valid payload → 201
- ✅ Test 2: Same payload → 200 (idempotency)
- ✅ Test 3: Malformed payload (missing sha256_hash) → 422
- ✅ Test 4: Media upload with correct hash → 200 + server_sha256 matches
- ✅ Test 5: Media upload with wrong declared hash → 422
- ✅ Additional tests for edge cases and validation

✅ **Bonus: LCA Engine (Prompt 8)**
- Pure Python math implementation
- Biochar carbon credit calculation
- Feedstock-specific parameters (Lantana_camara, Wood_chips, Agricultural_waste)
- Moisture adjustment calculations
- Process emissions accounting
- Net CO2e credit calculation in tonnes
- 17 comprehensive unit tests

## 📊 Test Results

```
27 tests passed in 0.62 seconds

API Tests (10/10 PASSED):
✅ test_health_check
✅ test_valid_payload_returns_201
✅ test_duplicate_idempotency_key_returns_200
✅ test_missing_sha256_hash_returns_422
✅ test_invalid_moisture_percent_returns_422
✅ test_missing_idempotency_key_returns_422
✅ test_media_upload_correct_hash_returns_200
✅ test_media_upload_wrong_hash_returns_422
✅ test_media_duplicate_idempotency_key
✅ test_extra_field_forbidden_returns_422

LCA Engine Tests (17/17 PASSED):
✅ All feedstock parameter tests
✅ All moisture adjustment tests
✅ All carbon sequestration calculations
✅ All validation tests
✅ All edge case tests
```

## 📁 Project Structure

```
/app/
├── backend/
│   ├── server.py              # FastAPI application
│   ├── models.py              # SQLAlchemy models
│   ├── db.py                  # Database configuration
│   ├── lca_engine.py          # LCA carbon credit calculator
│   ├── requirements.txt       # Python dependencies
│   ├── .env                   # Environment configuration
│   ├── alembic.ini            # Alembic migration config
│   ├── README.md              # Backend documentation
│   ├── tests/
│   │   ├── test_api.py        # API endpoint tests
│   │   └── test_lca_engine.py # LCA calculation tests
│   └── uploads/               # Media file storage
├── phase7_fixed/              # Original Flutter app context
├── DEPLOYMENT.md              # Production deployment guide
└── PROJECT_README.md          # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+

### Installation

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Start PostgreSQL:**
```bash
sudo service postgresql start
sudo -u postgres psql -c "CREATE DATABASE dmrv;"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
```

3. **Configure environment:**
```bash
# backend/.env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dmrv
```

4. **Run server:**
```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

5. **Access API docs:**
```
http://localhost:8001/api/docs
```

### Run Tests

```bash
cd backend
pytest tests/ -v
```

## 📡 API Endpoints

### Health Check
```bash
curl http://localhost:8001/api/health
```

### Submit Batch
```bash
curl -X POST http://localhost:8001/api/v1/batches \
  -H "X-Idempotency-Key: test-123" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "feedstock_species": "Lantana_camara",
    "harvest_timestamp": "2026-01-15T08:30:00Z",
    "moisture_percent": 12.5,
    "photo_path": "/sandbox/evidence/test.jpg",
    "sha256_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "harvest_uptime_seconds": 3600
  }'
```

### Upload Media
```bash
curl -X POST http://localhost:8001/api/v1/media \
  -H "X-Idempotency-Key: media-456" \
  -H "X-Declared-SHA256: $(sha256sum test.jpg | cut -d' ' -f1)" \
  -F "file=@test.jpg"
```

## 🧮 LCA Engine

The LCA engine calculates net carbon credits using biochar dMRV methodology:

**Formula:**
```
Net CO2e (tonnes) = [(Dry Mass × Yield × Carbon Content × Stability) × 3.667] - Emissions
                    ----------------------------------------------------------------
                                          1000
```

**Example Calculation:**
- Feedstock: Lantana_camara, 100kg at 12.5% moisture
- Dry mass: 87.5 kg
- Biochar yield: 25% = 21.875 kg
- Carbon content: 45% = 9.844 kg carbon
- Stability: 90% = 8.859 kg stable carbon
- CO2e sequestered: 8.859 × 3.667 = 32.48 kg CO2e
- Process emissions: 87.5 × 0.08 = 7.0 kg CO2e
- **Net credit: (32.48 - 7.0) / 1000 = 0.0255 tonnes CO2e**

## 🔒 Security Features

- Strict Pydantic validation with `extra="forbid"`
- SHA-256 integrity verification for uploads
- Idempotency to prevent duplicate processing
- CORS middleware configured
- SQL injection protection via SQLAlchemy ORM
- Input sanitization and type checking

## 📊 Database Schema

### Batches Table
- `batch_uuid` (UUID, unique)
- `operation_id` (string, unique) - for idempotency
- Payload fields: feedstock_species, harvest_timestamp, moisture_percent, etc.
- `net_credit_t_co2e` (float) - calculated carbon credit
- `status` (string) - processing status
- `received_at` (timestamp)

### Media Files Table
- `operation_id` (string, unique) - for idempotency
- `file_path` (text)
- `sha256_hash` (string, 64 chars)
- `filename` (string)
- `uploaded_at` (timestamp)

## 📚 Documentation

- **Backend README**: `/app/backend/README.md` - Complete API documentation
- **Deployment Guide**: `/app/DEPLOYMENT.md` - Production deployment instructions
- **API Docs**: `http://localhost:8001/api/docs` - Interactive Swagger UI
- **OpenAPI Spec**: `http://localhost:8001/api/openapi.json`

## 🧪 Testing Strategy

1. **Unit Tests** - LCA engine calculations
2. **Integration Tests** - API endpoints with test database
3. **Idempotency Tests** - Duplicate request handling
4. **Validation Tests** - Pydantic schema enforcement
5. **Error Handling Tests** - 422, 400 error responses

## 🚢 Deployment

See `DEPLOYMENT.md` for:
- Docker deployment
- Kubernetes deployment
- Cloud deployment (AWS, GCP, Heroku)
- Production configuration
- Monitoring and logging
- Security checklist
- Scaling strategies

## 🔧 Technology Stack

- **Framework**: FastAPI 0.115.6
- **Database**: PostgreSQL 15+ with asyncpg
- **ORM**: SQLAlchemy 2.0.36 (async)
- **Validation**: Pydantic V2.10.5
- **Testing**: pytest 8.3.4 + pytest-asyncio 0.25.2
- **Server**: Uvicorn with uvloop and httptools

## 📈 Performance

- Async/await throughout for non-blocking I/O
- Connection pooling for database
- Efficient SHA-256 calculation
- Minimal dependencies for fast startup
- Production-ready with uvicorn workers

## 🎓 Key Implementation Details

1. **Idempotency**: Uses unique `operation_id` with database-level UNIQUE constraint
2. **Race Conditions**: Handled via IntegrityError catch and refetch
3. **Schema Validation**: Pydantic V2 with strict field constraints
4. **SHA-256 Verification**: Server recalculates hash and compares
5. **LCA Calculations**: Pure Python math with feedstock-specific parameters

## 📝 Notes

- All tests pass (27/27)
- PostgreSQL required for production
- SQLite used for testing (in-memory)
- Media files stored locally (production should use object storage)
- LCA calculations based on biochar dMRV methodology research

## 🤝 Integration with Flutter

The Flutter app (in `phase7_fixed/`) generates payloads that match the API schema. The backend:
- Validates all incoming data strictly
- Provides idempotency for offline-first mobile sync
- Calculates carbon credits automatically
- Stores evidence files with integrity verification

## ✅ Requirements Checklist

- [x] FastAPI with SQLAlchemy async + PostgreSQL
- [x] Alembic migration support
- [x] Strict Pydantic V2 BatchPayload model
- [x] POST /api/v1/batches with idempotency
- [x] POST /api/v1/media with SHA-256 verification
- [x] 5 required pytest tests (+ 22 additional tests)
- [x] LCA engine with pure Python math
- [x] All tests passing
- [x] Production-ready code
- [x] Comprehensive documentation

## 📦 Ready for Production

This implementation is production-ready with:
- Comprehensive error handling
- Logging configured
- Database migrations support
- Security best practices
- Scalable architecture
- Complete test coverage
- Deployment documentation

---

**Built with ❤️ for sustainable biochar production and carbon credit tracking**
