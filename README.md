# Agentic Google Workspace Orchestrator

An intelligent orchestrator that executes natural language queries across Gmail, Google Calendar, and Google Drive.

## Features

- 🧠 **Intent Classification** - LLM-powered natural language understanding
- 🏗️ **Architect DAG Planner** - Zero-shot parallel execution plan generation
- 🛠️ **MCP Tool Registry** - Standardized, dynamic discovery of agent capabilities
- 🔄 **Query Orchestration** - Parallel execution with strict dependency resolution
- 🔍 **Hybrid Search** - Vector similarity + keyword filtering with pgvector
- 📧 **Gmail Agent** - Search, draft, send emails
- 📅 **Calendar Agent** - Search, create, update events
- 📁 **Drive Agent** - Search, share, organize files
- 📊 **Execution Trace UI** - Visual breakdown of parallel vs sequential operations
- ⚡ **Caching** - Redis caching for embeddings and intents
- 🚦 **Rate Limiting** - Sliding window rate limiter
- 🐳 **Dockerized** - Instant setup with mock data auto-seeding

## Quick Start

### 1. Clone and Setup

```bash
cd project4
cp .env.example .env
# Edit .env with your OpenAI API key
```

### 2. Start Everything
```bash
docker-compose up --build
```

### 3. Access
- **Testing UI**: [http://localhost:5173](http://localhost:5173) (Interactive query interface & data viewer)
- **API**: [http://localhost:8000](http://localhost:8000)
- **Docs**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)

## 🖥️ Testing UI
The project includes a modern **Vue 3 + Vite** testing dashboard designed for developers to:
- **Execute Queries**: Submit natural language intents and see the breakdown of classification.
- **Trace Execution**: Visualize the execution plan (Parallel vs Sequential) and time taken.
- **Inspect Database**: Live view of cached data from Gmail, Calendar, and Drive, focused on columns used for vector embeddings.
- **Auto-Seeding**: Upon first startup, the system automatically seeds the database with mock data for immediate testing.

## API Endpoints

### Query Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is on my calendar next week?"}'
```

### Search Endpoint

```bash
curl "http://localhost:8000/api/v1/search?q=flight+booking&service=gmail"
```

### Sample Queries

| Query | Description |
|-------|-------------|
| "What's on my calendar next week?" | Search calendar events |
| "Find emails from sarah@company.com" | Search emails by sender |
| "Cancel my Turkish Airlines flight" | Multi-service orchestration |
| "Prepare for tomorrow's Acme Corp meeting" | Aggregates from all services |

## Architecture

```
User Query → Intent Classifier → Query Planner → Service Orchestrator
                                                         ↓
                                          Gmail / GCal / Drive Agents
                                                         ↓
                                          Response Synthesizer → Response
```

## Project Structure

```
app/
├── main.py              # FastAPI application
├── config.py            # Settings management
├── database.py          # Database connection
├── api/                 # API endpoints
├── agents/              # Service agents (Gmail, GCal, Drive)
├── services/            # Business logic
│   ├── intent_classifier.py
│   ├── query_planner.py
│   ├── orchestrator.py
│   ├── response_synthesizer.py
│   ├── embedding_service.py
│   └── search_service.py
└── tasks/               # Celery background tasks
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM | Required |
| `DATABASE_URL` | PostgreSQL connection | See .env.example |
| `REDIS_URL` | Redis connection | redis://redis:6379/0 |
| `RATE_LIMIT_QUERIES_PER_HOUR` | Rate limit per user | 100 |

## Development

### Run Tests

```bash
docker-compose exec api pytest tests/ -v
```

### View Logs

```bash
docker-compose logs -f api
```

### Stop Services

```bash
docker-compose down
```

## Documentation

- [DESIGN.md](DESIGN.md) - Scaling strategy for 1M users
- [API.md](API.md) - API endpoint documentation

## License

MIT
