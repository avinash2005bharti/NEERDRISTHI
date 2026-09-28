# ORCA Local Development Setup Guide

> **SIH26176 Project:** ORCA (Marine Ecosystem Reasoning with Collaborative Agents)

This guide covers running the complete ORCA backend monorepo locally with or without Docker.

---

## 1. Prerequisites

Ensure your host machine has the following tools installed:
- **Node.js:** v20.x or higher (`node -v`)
- **npm** (v10+) or **pnpm** (v9+)
- **Python:** v3.11 or higher (`python --version`)
- **MongoDB:** MongoDB Community Server (v7+) running locally on `localhost:27017` OR a MongoDB Atlas cluster URI.
- **Docker & Docker Compose** *(optional, for containerized local runtime)*

---

## 2. Directory Structure

```text
orca-backend/
├── package.json
├── pnpm-workspace.yaml
├── docker-compose.yml
├── apps/
│   ├── gateway/         # Node.js Express + Socket.IO API Gateway (Port 3001)
│   └── agent-core/      # Python FastAPI + LangGraph Agent Core (Port 8000)
├── packages/
│   └── contracts/       # Shared TypeScript API & Socket.IO contracts
└── docs/                # Architecture, APIs, Sockets, and Safety policies
```

---

## 3. Environment Configuration

Copy the example environment files in both applications:

### 3.1 Gateway Service
```bash
cd apps/gateway
copy .env.example .env     # Windows
# or: cp .env.example .env # macOS/Linux
```
Open `apps/gateway/.env` and configure:
```env
NODE_ENV=development
GATEWAY_PORT=3001
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=orca
JWT_SECRET=supersecret-dev-jwt-key-replace-in-production
FASTAPI_INTERNAL_URL=http://localhost:8000
INTERNAL_SERVICE_SECRET=shared-secret-between-services
```

### 3.2 Agent Core Service
```bash
cd ../agent-core
copy .env.example .env     # Windows
# or: cp .env.example .env # macOS/Linux
```
Open `apps/agent-core/.env` and configure:
```env
APP_ENV=development
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
INTERNAL_SERVICE_SECRET=shared-secret-between-services
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=orca
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
```

> **Note on Blank API Keys:** You can run the entire system with blank external API keys! ORCA is explicitly designed to handle unconfigured feeds gracefully and return structured `DATA_UNAVAILABLE` states without crashing.

---

## 4. Local Startup Without Docker

### Step 1: Build Shared Contracts
```bash
cd packages/contracts
npm install
npm run build
```

### Step 2: Start Node.js API Gateway
In a new terminal:
```bash
cd apps/gateway
npm install
npm run dev
```
The gateway will start on **http://localhost:3001**.

### Step 3: Start Python Agent Core
In a second terminal:
```bash
cd apps/agent-core
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The Agent Core will start on **http://localhost:8000**. Interactive OpenAPI docs are at **http://localhost:8000/docs**.

---

## 5. Local Startup With Docker Compose

To run all services (MongoDB, Redis, Agent Core, and Gateway) inside isolated local containers:

```bash
cd orca-backend
docker-compose up --build
```

Local ports exposed on `localhost`:
- **Gateway:** `http://localhost:3001`
- **Agent Core:** `http://localhost:8000`
- **MongoDB:** `localhost:27017`
- **Redis:** `localhost:6379`

---

## 6. Verifying System Health

### 1. Gateway Health Check
```bash
curl http://localhost:3001/api/v1/health
```
Expected output:
```json
{
  "status": "ok",
  "service": "orca-gateway",
  "version": "1.0.0",
  "components": {
    "database": { "type": "mongodb", "status": "connected" },
    "agentCore": { "url": "http://localhost:8000", "status": "healthy" }
  }
}
```

### 2. Submit a Test Query
```bash
curl -X POST http://localhost:3001/api/v1/orca/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Is it safe to go fishing off Visakhapatnam today?",
    "location": { "name": "Visakhapatnam Harbor", "latitude": 17.68, "longitude": 83.21 },
    "userProfile": { "role": "fisherman", "vesselClass": "motorized_fiberglass" }
  }'
```
With empty external API credentials, this will safely return recommendation: `INSUFFICIENT_DATA`, correctly identifying that real telemetry feeds are offline.

---

## 7. Running the Test Suite

### Python Agent Core Tests
```bash
cd apps/agent-core
# Activate venv:
.venv\Scripts\activate # (or source .venv/bin/activate)
pytest app/tests -v
```

All tests execute against local mock fixtures and **never call paid external APIs**.
