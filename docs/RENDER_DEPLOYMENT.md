# Deploying ORCA / NEERDRISTHI on Render

This guide provides step-by-step instructions for deploying the complete, multi-tier **ORCA / NEERDRISTHI (SIH 26176)** platform on [Render](https://render.com) using a single GitHub repository and one Render Blueprint (`render.yaml`).

---

## 🏗️ Target Architecture on Render

```
GitHub Repository (avinash2005bharti/NEERDRISTHI)
   │
   └── render.yaml (Blueprint)
         ├── 1. orca-frontend  [Static Site]         React 18 + Vite (SPA)
         ├── 2. orca-backend   [Web Service - Node]  Express + Socket.IO Gateway
         └── 3. orca-ai        [Web Service - Python] FastAPI + LangGraph Cognitive Core
```

- **`orca-frontend`**: Serves the compiled React Vite Single Page Application directly from Render's global CDN.
- **`orca-backend`**: High-throughput REST & Socket.IO realtime server running Node.js 20+, handling authentication, rate-limiting, MongoDB state, and WebSocket telemetry.
- **`orca-ai`**: Python 3.11+ FastAPI service running LangGraph collaborative multi-agent workflows, GeoPandas spatial intelligence, and deterministic safety rules.

---

## 📋 Prerequisites

Before starting, ensure you have:
1. A **GitHub account** with access to this repository.
2. A free **Render account** at [render.com](https://render.com).
3. A **MongoDB Atlas** cluster connection URI (Free M0 tier from [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)).
4. *(Optional but recommended)* A free **Groq Cloud API key** from [console.groq.com](https://console.groq.com) for multilingual LLM synthesis.
5. *(Optional)* A free **Qdrant Cloud cluster** from [cloud.qdrant.io](https://cloud.qdrant.io) for long-term vector memory.

---

## 🚀 One-Click Blueprint Deployment Steps

### Step 1: Push Repository to GitHub
Ensure your repository is pushed to GitHub:
```bash
git push origin main
```

### Step 2: Create a New Blueprint in Render
1. Log in to your [Render Dashboard](https://dashboard.render.com).
2. In the top-right corner, click **New +** and select **Blueprint**.
3. Connect your GitHub account (if not already connected) and select the repository: `avinash2005bharti/NEERDRISTHI`.
4. Branch: select **`main`**.

### Step 3: Review Blueprint Services
Render will automatically detect `render.yaml` at the root of the repository and configure all three services:
1. `orca-frontend` (Static Site, Root Directory: `frontend`)
2. `orca-backend` (Web Service, Root Directory: `backend/server`)
3. `orca-ai` (Web Service, Root Directory: `backend/ai-services`)

### Step 4: Configure Environment Secrets
Render will prompt you for the environment variables marked with `sync: false`:

| Variable Name | Service | Description / Example |
| :--- | :--- | :--- |
| `MONGODB_URI` | `orca-backend` & `orca-ai` | `mongodb+srv://<user>:<password>@cluster0.mongodb.net/orca?retryWrites=true&w=majority` |
| `GROQ_API_KEY` | `orca-ai` | Your free Groq API key (`gsk_...`) |
| `QDRANT_URL` | `orca-ai` | *(Optional)* Qdrant cluster endpoint |
| `QDRANT_API_KEY` | `orca-ai` | *(Optional)* Qdrant Cloud API key |

> **Note on Auto-Generated Secrets:**  
> Render automatically generates strong, unique cryptographic values for `JWT_SECRET` and `INTERNAL_SERVICE_SECRET`, and automatically shares them between `orca-backend` and `orca-ai`. You do not need to configure them manually.

### Step 5: Click "Apply"
Click **Apply**. Render will concurrently build and deploy:
- The static frontend site (`npm install && npm run build`)
- The Node.js gateway (`npm install`)
- The Python AI agent core (`pip install -r requirements.txt`)

---

## 🔍 Service URLs & Health Verification

Once deployment completes, your services will be live:

### 1. Frontend Client
- **URL**: `https://orca-frontend-51u4.onrender.com`
- **Verification**: Open in your browser; verify that the login screen, interactive marine map, and navigation render properly.

### 2. Node.js API Gateway
- **Health Check**: `https://orca-backend-9ezw.onrender.com/health`
- **Expected Response**:
  ```json
  {
    "status": "ok",
    "service": "orca-gateway",
    "version": "1.0.0",
    "components": {
      "database": { "type": "mongodb", "status": "connected" },
      "agentCore": { "status": "healthy" }
    }
  }
  ```

### 3. Python FastAPI Agent Core
- **Lightweight Health Check**: `https://orca-aiservices.onrender.com/health`
- **Expected Response**:
  ```json
  {
    "status": "ok",
    "service": "orca-ai",
    "environment": "production"
  }
  ```
- **Readiness Check**: `https://orca-aiservices.onrender.com/ready`
- **Detailed Component Diagnostic**: `https://orca-aiservices.onrender.com/health/detail`
- **Interactive API Docs**: `https://orca-aiservices.onrender.com/docs`

---

## 🧪 Post-Deployment Functional Testing

1. **User Authentication**:
   - Navigate to `https://orca-frontend-51u4.onrender.com`.
   - Register a new account (e.g., Role: `Fisherman`, Vessel: `Motorized Fiberglass`).
   - Log in and verify JWT persistence in browser localStorage.
2. **Marine Safety Query**:
   - On the Chat tab, ask: *"Is it safe to depart from Sassoon Docks Mumbai right now?"*
   - Watch the multi-agent pipeline stream live execution stages (`planner`, `geospatial`, `weather`, `marine`, `safety`, `synthesis`).
   - Verify deterministic verdict (`GO`, `GO_WITH_CAUTION`, or `NO_GO`) and explainable multilingual advisory (English, Hindi, Marathi).
3. **Interactive Marine Map**:
   - Navigate to the **Map** tab.
   - Toggle layers: Sea Surface Temperature (SST), Chlorophyll-a heatmap, Wave height, and Military Restricted Geofences (Wheeler Island, Palk Bay IMBL).
4. **Emergency SOS**:
   - Click the red **SOS** beacon in the navigation header.
   - Verify that GPS coordinates and Indian Coast Guard emergency instructions (SAR Helpline 1554 / VHF Ch 16) appear.

---

## 🛠️ Troubleshooting & Technical Notes

### 1. Render Free Tier Spin-Down & Cold-Start Architecture
- Render web services on the free tier spin down after 15 minutes of inactivity.
- On cold start, the Node.js API Gateway utilizes a **bounded exponential backoff retry strategy** (up to 3 retries over 20–45s) to transparently absorb the container allocation window without dropping user requests.
- The Python AI core uses an **ultra-lightweight, non-blocking startup** (`GET /health` responds in <1ms without loading models or awaiting remote DBs), allowing Render's load balancer to instantly detect the port and route incoming traffic.
- If the AI service is in the middle of booting and cannot be reached after all retries, the Gateway returns a structured `503 AI_SERVICE_UNAVAILABLE` with clear retry guidance rather than throwing an unhandled exception.

### 2. WebSocket & Socket.IO Connectivity
- Socket.IO is configured to support both `websocket` and `polling` transports.
- If WebSocket upgrade is delayed by proxy firewalls, Socket.IO gracefully falls back to long-polling without disconnecting the user.

### 3. Zero-Key Open Data Resiliency
- Open-Meteo Weather & Marine, INCOIS ERDDAP, and OpenStreetMap operate without private API keys.
- If an external scientific feed times out, the `MarineDataGateway` automatically triggers retry backoff and falls back to MET Norway or local benchmarks without crashing the service.

### 4. Updating Deployed Code
- Every `git push origin main` triggers automatic redeployment across all three services.
- If you only modified frontend files, Render's build cache ensures lightning-fast builds.
