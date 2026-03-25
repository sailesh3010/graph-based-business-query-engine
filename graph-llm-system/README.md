# 🔗 Graph-Based O2C Data Modeling & LLM Query System

An interactive **Order-to-Cash (O2C) graph explorer** with an **AI-powered natural language query interface**. Built as a full-stack application that unifies fragmented SAP business data into a graph and lets users explore relationships and ask questions in plain English.

![Dodge AI — Order to Cash](./screenshot.png)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│              React + Vite Frontend               │
│  ┌──────────────────┬──────────────────────┐    │
│  │  Graph Viz        │  Chat Interface      │    │
│  │  react-force-graph│  NL queries → answers│    │
│  └──────────────────┴──────────────────────┘    │
└────────────────┬────────────────────────────────┘
                 │ REST API (proxied via Vite)
┌────────────────▼────────────────────────────────┐
│           Python FastAPI Backend                 │
│  ┌────────┬───────────┬───────────────────┐     │
│  │ Graph  │ LLM       │ Guardrails        │     │
│  │Builder │ (Gemini)  │ (domain filter)   │     │
│  │NetworkX│ NL → SQL  │                   │     │
│  └───┬────┴─────┬─────┴───────────────────┘     │
│      │          │                                │
│  ┌───▼──────────▼─────────────────────────┐     │
│  │         PostgreSQL Database             │     │
│  │  19 tables, ~21K records, 29 indexes    │     │
│  └─────────────────────────────────────────┘     │
└──────────────────────────────────────────────────┘
```

## 📊 Tech Stack & Rationale

| Component | Choice | Why |
|-----------|--------|-----|
| **Database** | PostgreSQL | Production-grade RDBMS with CTEs, window functions, and recursive queries for complex O2C flow tracing |
| **Backend** | FastAPI (Python) | Async-capable, excellent for LLM integration, clean API design |
| **Graph Engine** | NetworkX | In-memory graph processing, fast traversal, easy serialization |
| **LLM** | Google Gemini 2.0 Flash (free tier) | Strong SQL generation, generous free limits |
| **Frontend** | React + Vite | Fast HMR, modern tooling |
| **Graph Viz** | react-force-graph-2d | Interactive force-directed layout with canvas rendering |

## 🧠 Graph Model

**11 Entity Types (Nodes):**
- **Core Flow:** SalesOrder → SalesOrderItem → Delivery → DeliveryItem → BillingDocument → BillingDocumentItem → JournalEntry → Payment
- **Supporting:** Customer, Product, Plant

**16 Relationship Types (Edges):**
- `ordered_by`, `has_item`, `for_product`, `produced_at`, `delivers_order`, `shipped_from`, `bills_order`, `billed_to`, `generates_entry`, `for_customer`, `paid_by`, `pays_invoice`

## 🤖 LLM Prompting Strategy

### NL → SQL Pipeline
1. **Guardrail pre-filter** — Keyword matching + off-topic pattern detection blocks irrelevant queries before reaching the LLM
2. **Schema-aware system prompt** — Compact PostgreSQL schema with all table/column definitions and relationship mappings
3. **Structured JSON output** — LLM returns `{thinking, sql, answer_template}` for reliable parsing
4. **SQL execution with retry** — If generated SQL fails, error is fed back to LLM for auto-correction
5. **Natural language response** — Query results are sent back to LLM for human-readable answers

### Guardrails
- **Pre-filter layer:** Domain keyword matching rejects clearly off-topic queries (recipes, poems, general knowledge) before any API call
- **LLM-level guardrails:** System prompt instructs the model to refuse non-dataset questions
- **Rejection message:** "This system is designed to answer questions related to the provided dataset only."
- **Read-only SQL execution:** All queries run with statement timeout and rollback

## 🚀 Setup & Run

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ running locally

### 1. Database Setup
```bash
# Create the database
psql -U postgres -c "CREATE DATABASE graph_system;"
```

### 2. Backend Setup
```bash
cd graph-llm-system/backend

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and PostgreSQL credentials

# Ingest data into PostgreSQL
python ingest.py

# Start the API server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd graph-llm-system/frontend

# Install dependencies
npm install

# Start dev server (proxies /api to backend)
npm run dev
```

### 4. Open the App
Navigate to **http://localhost:5173**

## 🐳 Deployment (Docker & Cloud)

The system is fully containerized for 1-click deployments. The FastAPI backend is configured to statically serve the built React frontend, allowing the entire application to run as a single web service.

### Local Docker Deployment
If you have Docker installed, simply run:
```bash
docker-compose up --build
```
This will spin up a PostgreSQL database, automatically ingest the dataset, build the Vite frontend, and launch the unified FastAPI server on `http://localhost:8000`.

### Cloud Deployment (Render.com)
You can deploy this repository live to the internet for free using [Render](https://render.com):
1. Connect your GitHub repository to Render.
2. Create a **PostgreSQL** instance (Free Tier).
3. Create a **Web Service** mapped to this repository.
    - **Environment**: Docker
    - **Environment Variables**:
      - `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST` (Matches the Postgres DB)
      - `GEMINI_API_KEY` = `your-api-key`

## 💬 Example Queries

- "Which products are associated with the highest number of billing documents?"
- "Trace the full flow of billing document 9050000249"
- "Identify sales orders that have broken or incomplete flows"
- "What is the total revenue by customer?"
- "Show deliveries that were not billed"
- "List all plants and their associated products"

## 📁 Project Structure

```
graph-llm-system/
├── backend/
│   ├── main.py              # FastAPI app with all endpoints
│   ├── database.py          # PostgreSQL connection & query helpers
│   ├── ingest.py            # JSONL → PostgreSQL data pipeline
│   ├── graph_builder.py     # NetworkX graph construction
│   ├── llm_service.py       # Gemini NL→SQL→answer pipeline
│   ├── guardrails.py        # Domain validation & off-topic rejection
│   ├── requirements.txt     # Python dependencies
│   └── .env                 # API keys & DB credentials
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main layout coordinator
│   │   ├── main.jsx          # React entry point
│   │   ├── index.css         # Design system (glassmorphism, animations)
│   │   └── components/
│   │       ├── GraphView.jsx  # Force-directed graph + controls
│   │       ├── ChatPanel.jsx  # Chat UI with markdown rendering
│   │       └── NodeDetail.jsx # Node metadata popover
│   ├── index.html            # HTML entry with Inter font
│   ├── vite.config.js        # Vite + API proxy config
│   └── package.json
├── sap-o2c-data/             # Raw JSONL dataset (19 entity folders)
└── README.md
```
