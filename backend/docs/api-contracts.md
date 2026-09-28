# ORCA REST API Contracts

This document provides the formal REST API specification for both public frontend integration via the Node.js Gateway and internal communication with the Python Agent Core.

---

## 1. Gateway Public REST Endpoints (`http://localhost:3001/api/v1`)

### 1.1 `GET /api/v1/health`
Check Gateway health, MongoDB persistence status, and upstream Agent Core connectivity.

**Request:** `GET /api/v1/health`

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "service": "orca-gateway",
  "version": "1.0.0",
  "timestamp": "2026-09-24T12:00:00.000Z",
  "components": {
    "database": {
      "type": "mongodb",
      "status": "connected"
    },
    "agentCore": {
      "url": "http://localhost:8000",
      "status": "healthy"
    }
  }
}
```

---

### 1.2 `POST /api/v1/auth/register`
Register a new coastal user (fisherman, authority, disaster manager, or admin).

**Request (`POST`):**
```json
{
  "email": "raman.fisherman@example.in",
  "password": "SecurePassword123!",
  "name": "Raman K",
  "role": "fisherman",
  "vesselClass": "motorized_fiberglass",
  "preferredLanguage": "ta"
}
```

**Response (`201 Created`):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "e5c707db-5d07-4e7d-94c0-26477e6db076",
      "email": "raman.fisherman@example.in",
      "name": "Raman K",
      "role": "fisherman",
      "vesselClass": "motorized_fiberglass",
      "preferredLanguage": "ta",
      "createdAt": "2026-09-24T12:00:00.000Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresIn": "7d"
  },
  "meta": {
    "requestId": "a001",
    "timestamp": "2026-09-24T12:00:00.000Z"
  }
}
```

---

### 1.3 `POST /api/v1/auth/login`
Authenticate existing user and obtain a JWT bearer token.

**Request (`POST`):**
```json
{
  "email": "raman.fisherman@example.in",
  "password": "SecurePassword123!"
}
```

**Response (`200 OK`):** Same shape as register response with JWT token.

---

### 1.4 `POST /api/v1/orca/query`
Primary query endpoint for marine advisory, safety checks, and fishing zone navigation.

**Headers:**
- `Content-Type: application/json`
- `Authorization: Bearer <JWT_TOKEN>` *(optional for guest access)*

**Request Payload:**
```json
{
  "conversationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "query": "Is it safe to sail from Chennai harbor towards Mahabalipuram for tuna fishing tomorrow morning?",
  "intent": "safety_check",
  "location": {
    "name": "Chennai Harbor",
    "latitude": 13.0827,
    "longitude": 80.2707
  },
  "timeWindow": {
    "start": "2026-09-25T05:00:00Z",
    "end": "2026-09-25T11:00:00Z",
    "label": "tomorrow_morning"
  },
  "userProfile": {
    "role": "fisherman",
    "vesselClass": "motorized_fiberglass",
    "language": "en"
  },
  "route": {
    "type": "LineString",
    "coordinates": [
      [80.2707, 13.0827],
      [80.2900, 12.9000],
      [80.1983, 12.6174]
    ]
  }
}
```

**Response (`200 OK`):**
```json
{
  "success": true,
  "data": {
    "requestId": "d820df11-2d7c-48c9-83c0-39499ff36c28",
    "conversationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "partial",
    "recommendation": "INSUFFICIENT_DATA",
    "riskLevel": "UNKNOWN",
    "riskScore": 75,
    "confidenceScore": 15,
    "answer": "ORCA Safety Evaluation: [INSUFFICIENT_DATA] (Risk Level: UNKNOWN, Score: 75/100, Confidence: 15%).\nVessel Class: motorized_fiberglass.\nTelemetry gaps identified: Live Weather & Sea-State Telemetry (Wind speed, Wave height).\nDirective: Do NOT venture out to sea without verified local port meteorological clearance. Awaiting official IMD/INCOIS feed connectivity.",
    "language": "en",
    "clarificationQuestion": null,
    "dataAvailability": {
      "marine": "unavailable",
      "weather": "unavailable",
      "tide": "unavailable",
      "geospatial": "available",
      "semanticMemory": "unavailable"
    },
    "evidence": [
      {
        "category": "geospatial",
        "name": "Coordinate Resolution",
        "value": { "longitude": 80.2707, "latitude": 13.0827 },
        "unit": null,
        "observedAt": null,
        "validUntil": null,
        "retrievedAt": "2026-09-24T12:00:00.000Z",
        "sourceName": "Coastal Coordinate Validator",
        "sourceUrl": null,
        "freshness": "fresh"
      }
    ],
    "safety": {
      "triggeredRules": [
        "Missing critical telemetry policy: Weather/sea-state data unavailable. Defaulting to INSUFFICIENT_DATA"
      ],
      "missingData": [
        "Live Weather & Sea-State Telemetry (Wind speed, Wave height)"
      ],
      "requiredNextAction": "Do NOT venture out to sea without verified local port meteorological clearance. Awaiting official IMD/INCOIS feed connectivity."
    },
    "trace": {
      "requestId": "d820df11-2d7c-48c9-83c0-39499ff36c28",
      "agentStatuses": [
        { "agent": "planner", "status": "completed", "timestamp": "2026-09-24T12:00:01Z" },
        { "agent": "geospatial", "status": "completed", "timestamp": "2026-09-24T12:00:01Z" },
        { "agent": "marine_pfz", "status": "failed", "timestamp": "2026-09-24T12:00:02Z" },
        { "agent": "weather_sea_state", "status": "failed", "timestamp": "2026-09-24T12:00:02Z" },
        { "agent": "semantic_memory", "status": "skipped", "timestamp": "2026-09-24T12:00:02Z" },
        { "agent": "safety_risk_engine", "status": "completed", "timestamp": "2026-09-24T12:00:03Z" },
        { "agent": "synthesis", "status": "completed", "timestamp": "2026-09-24T12:00:03Z" }
      ],
      "startedAt": "2026-09-24T12:00:00.000Z",
      "completedAt": "2026-09-24T12:00:03.000Z"
    }
  },
  "meta": {
    "requestId": "d820df11-2d7c-48c9-83c0-39499ff36c28",
    "timestamp": "2026-09-24T12:00:03.000Z"
  }
}
```

---

### 1.5 `GET /api/v1/orca/query/:requestId`
Retrieve a previously executed query response by `requestId`.

---

### 1.6 `GET /api/v1/orca/conversations/:conversationId`
Retrieve the chronological conversation history and audit chain for a specific session.

---

## 2. Agent Core Internal REST Endpoints (`http://localhost:8000`)

Protected by `x-internal-service-secret`.

### 2.1 `GET /health`
Returns provider configuration diagnostics.

### 2.2 `POST /internal/v1/orca/execute`
Dispatches the query through the multi-agent LangGraph workflow.

**Required Header:**
`x-internal-service-secret: <MATCHING_SECRET>`

### 2.3 `GET /internal/v1/orca/request/{request_id}`
Returns cached query execution results from MongoDB.
