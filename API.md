# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints require authentication. Use the OAuth flow to obtain tokens.

```bash
# Start OAuth flow
GET /auth/google

# Check auth status  
GET /auth/status
```

---

## Endpoints

### POST /query

Process a natural language query across Google Workspace services.

**Request:**

```json
{
  "query": "What's on my calendar next week?",
  "conversation_id": "optional-uuid"
}
```

**Response:**

```json
{
  "conversation_id": "uuid",
  "response": "Found **5** events for next week:\n📅 **Team Standup** - Mon 9:00 AM\n...",
  "intent": {
    "services": ["gcal"],
    "intent": "search_events",
    "entities": {"time_reference": "next week"},
    "steps": ["search_events"],
    "confidence": 0.95
  },
  "actions_taken": [],
  "execution_time_ms": 342
}
```

**Example Queries:**

| Query | Intent | Services |
|-------|--------|----------|
| "What's on my calendar next week?" | search_events | gcal |
| "Find emails from sarah@company.com" | search_emails | gmail |
| "Show me PDFs from last month" | search_files | gdrive |
| "Cancel my Turkish Airlines flight" | cancel_flight | gmail, gcal |
| "Prepare for tomorrow's Acme meeting" | prepare_meeting | gmail, gcal, gdrive |

---

### GET /api/v1/search

Perform direct hybrid search across services using pgvector.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `q` | string | Search query (required) |
| `service` | string | Filter by service (gmail, gcal, gdrive) |
| `limit` | integer | Max results (default 10) |

**Example:**
`GET /api/v1/search?q=budget&service=gmail`

---

### POST /sync/trigger

Manually trigger data synchronization.

**Request:**

```json
{
  "services": ["gmail", "gcal"]
}
```

**Response:**

```json
{
  "success": true,
  "message": "Sync triggered for: gmail, gcal"
}
```

---

### GET /sync/status

Get synchronization status for all services.

**Response:**

```json
{
  "gmail": {
    "last_sync_at": "2024-01-15T10:30:00Z",
    "items_synced": 150,
    "status": "idle"
  },
  "gcal": {
    "last_sync_at": "2024-01-15T10:30:00Z", 
    "items_synced": 45,
    "status": "idle"
  },
  "gdrive": {
    "last_sync_at": "2024-01-15T10:30:00Z",
    "items_synced": 78,
    "status": "idle"
  }
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Missing required field: query"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 3600
}
```

### 500 Internal Server Error

```json
{
  "detail": "Failed to process query: ..."
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| POST /query | 100/hour/user |
| POST /sync/trigger | 10/hour/user |

---

## OpenAPI Spec

Interactive documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
