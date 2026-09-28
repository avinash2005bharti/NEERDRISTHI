# ORCA Realtime Socket.IO Events

The Node.js Gateway exposes a dedicated WebSocket namespace at `/orca` using **Socket.IO**. This allows the frontend to receive real-time, low-latency streaming updates as each agent in the LangGraph workflow initiates, gathers evidence, or encounters telemetry gaps.

---

## 1. Connection & Handshake Authentication

### Endpoint & Namespace
- **URL:** `ws://localhost:3001` or `http://localhost:3001`
- **Namespace:** `/orca`

### Handshake Authentication
Clients authenticate during the Socket.IO connection handshake by passing the JWT token in `auth.token`, `headers.authorization`, or query parameters.

#### Frontend Connection Example (React / TypeScript):
```typescript
import { io, Socket } from 'socket.io-client';

const socket: Socket = io('http://localhost:3001/orca', {
  auth: {
    token: localStorage.getItem('orca_jwt_token') || '',
  },
  transports: ['websocket', 'polling'],
});

socket.on('connect', () => {
  console.log('Connected to ORCA realtime gateway:', socket.id);
});
```

---

## 2. Server-to-Client Events

### 2.1 `orca:connected`
Emitted immediately upon successful connection.
```json
{
  "timestamp": "2026-09-24T12:00:00.000Z",
  "socketId": "aBcD1234EfGh",
  "userId": "e5c707db-5d07-4e7d-94c0-26477e6db076",
  "authenticated": true,
  "message": "Connected to ORCA Marine Intelligence Realtime Gateway"
}
```

---

### 2.2 `orca:query:accepted`
Emitted when a query is received and validated by the gateway.
```json
{
  "timestamp": "2026-09-24T12:00:01.000Z",
  "requestId": "d820df11-2d7c-48c9-83c0-39499ff36c28",
  "conversationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "accepted",
  "estimatedSteps": [
    "Query Intake & Planning",
    "Geospatial Coordinate Resolution",
    "Parallel Marine & Weather Observation Fetching",
    "Semantic Memory & Maritime Advisory Retrieval",
    "Deterministic Safety & Risk Rule Evaluation",
    "Multi-Agent Grounded Synthesis"
  ]
}
```

---

### 2.3 `orca:agent:started`
Emitted when an individual cognitive agent initiates execution.
```json
{
  "timestamp": "2026-09-24T12:00:01.500Z",
  "requestId": "d820df11-2d7c-48c9-83c0-39499ff36c28",
  "conversationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "agent": "planner",
  "agentLabel": "Query Intake & Multi-Agent Planner",
  "intent": "safety_check"
}
```

---

### 2.4 `orca:agent:progress`
Emitted when an agent completes a sub-milestone (e.g., coordinates resolved).
```json
{
  "timestamp": "2026-09-24T12:00:02.000Z",
  "requestId": "d820df11-2d7c-48c9-83c0-39499ff36c28",
  "conversationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "agent": "geospatial",
  "stage": "2dsphere_spatial_intersection",
  "message": "Validated 3 waypoints against designated restricted naval boundaries."
}
```

---

### 2.5 `orca:agent:completed`
Emitted when an agent completes its task.
```json
{
  "timestamp": "2026-09-24T12:00:02.500Z",
  "requestId": "d820df11-2d7c-48c9-83c0-39499ff36c28",
  "conversationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "agent": "marine_pfz",
  "status": "completed",
  "summary": "Processed 2 PFZ coordinates and SST bulletins from INCOIS."
}
```

---

### 2.6 `orca:data:unavailable`
**Critical Invariant Event:** Emitted whenever a real external telemetry feed is missing, disabled, rate-limited, or unconfigured.
```json
{
  "timestamp": "2026-09-24T12:00:02.800Z",
  "requestId": "d820df11-2d7c-48c9-83c0-39499ff36c28",
  "conversationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "category": "weather",
  "providerName": "METEOROLOGICAL_PROVIDER",
  "reason": "Official weather telemetry endpoint is unconfigured or returned no live data.",
  "impactOnRecommendation": "Policy mandates NO_GO or INSUFFICIENT_DATA due to missing critical observations."
}
```

---

### 2.7 `orca:clarification:required`
Emitted if the user's query lacks vital location or temporal anchors.
```json
{
  "timestamp": "2026-09-24T12:00:01.200Z",
  "requestId": "d820df11-2d7c-48c9-83c0-39499ff36c28",
  "conversationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "question": "Please specify your departure harbor, coastal location name, or GPS coordinates (latitude and longitude) to assess marine safety and fishing zones."
}
```

---

### 2.8 `orca:response:completed`
Emitted when the multi-agent reasoning graph terminates with full data coverage. Payload contains the complete `OrcaQueryResponse` object.

---

### 2.9 `orca:response:partial`
Emitted when reasoning completes with non-fatal data gaps (e.g. historical SOPs unavailable, but weather is live).

---

### 2.10 `orca:response:failed`
Emitted if an unhandled internal exception or system error halts the workflow.
```json
{
  "timestamp": "2026-09-24T12:00:03.000Z",
  "requestId": "d820df11-2d7c-48c9-83c0-39499ff36c28",
  "conversationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "error": {
    "code": "UPSTREAM_SERVICE_ERROR",
    "message": "The marine agent reasoning core is currently unreachable or timed out."
  }
}
```

---

## 3. Client-to-Server Events

### 3.1 `orca:query:submit`
Submit a new marine query directly over WebSocket.
```typescript
socket.emit(
  'orca:query:submit',
  {
    request: {
      query: "Is it safe to depart Kochi harbor today?",
      location: { name: "Kochi Harbor", latitude: 9.9667, longitude: 76.2400 },
      userProfile: { role: "fisherman", vesselClass: "motorized_fiberglass" }
    }
  },
  (ack) => {
    console.log('Server acknowledged query receipt:', ack);
  }
);
```

### 3.2 `orca:conversation:join`
Join a specific conversation room to receive multi-device streaming updates.
```typescript
socket.emit('orca:conversation:join', { conversationId: '3fa85f64...' }, (ack) => {
  console.log('Joined room:', ack);
});
```

### 3.3 `orca:conversation:leave`
Leave a previously joined conversation room.
```typescript
socket.emit('orca:conversation:leave', { conversationId: '3fa85f64...' });
```
