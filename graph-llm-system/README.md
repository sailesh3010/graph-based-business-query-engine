# 🔗 Graph-Based O2C Data Modeling & LLM Query System

An interactive **Order-to-Cash (O2C) graph explorer** with an **AI-powered natural language query interface**. Built as a full-stack application that unifies fragmented SAP business data into a graph and lets users explore relationships and ask questions in plain English.

![Dodge AI — Order to Cash](./screenshot.png)

## 🏗️ Architecture Decisions

Our architecture follows a clean separation of concerns, divided into a React frontend and a Python backend, prioritizing ease of development, responsiveness, and robust AI integration.

```text
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

**Key Architectural Choices:**
1. **FastAPI for the Backend:** Chosen for its native asynchronous capabilities, which are essential when orchestrating multiple latent I/O operations like LLM API calls and database queries. Its automatic OpenAPI documentation also streamlines frontend integration.
2. **React + Vite for the Frontend:** Vite provides instant server start and lightning-fast HMR, vastly improving the developer experience. React's component-based model is perfect for managing the complex state between the chat interface and the interactive graph visualization.
3. **NetworkX for Graph Processing:** While the data resides in a relational database, building an in-memory graph using NetworkX allows for fast traversal, algorithm execution, and easy serialization of sub-graphs for the frontend visualization without hammering the database with complex recursive queries.

## 📊 Database Choice: Why PostgreSQL?

| Component | Choice | Why |
|-----------|--------|-----|
| **Database** | PostgreSQL | Production-grade RDBMS with CTEs, window functions, and recursive queries for complex O2C flow tracing |
| **Backend** | FastAPI (Python) | Async-capable, excellent for LLM integration, clean API design |
| **Graph Engine** | NetworkX | In-memory graph processing, fast traversal, easy serialization |
| **LLM** | Google Gemini 2.0 Flash (free tier) | Strong SQL generation, generous free limits |
| **Frontend** | React + Vite | Fast HMR, modern tooling |
| **Graph Viz** | react-force-graph-2d | Interactive force-directed layout with canvas rendering |

While navigating an Order-to-Cash process feels like a graph problem, we chose **PostgreSQL**, a relational database, as the primary data store over a native graph database (like Neo4j) for several critical reasons:
1. **LLM SQL Proficiency:** Modern LLMs like Gemini are trained extensively on SQL data and schema structures. They are significantly better at generating accurate standard SQL than specialized graph query languages like Cypher.
2. **Relational Nature of Source Data:** The source SAP data consists of 19 structured, tabular JSONL files tightly bound by foreign keys. A relational schema naturally models this structure without requiring a complex ETL pipeline to map foreign keys to graph edges.
3. **Advanced SQL Features:** PostgreSQL supports Common Table Expressions (CTEs) and recursive queries, which provide sufficient graph-traversing capabilities (e.g., tracing a document flow) when needed, bridging the gap between relational storage and graph-like querying.

## 🧠 Graph Model

**11 Entity Types (Nodes):**
- **Core Flow:** SalesOrder → SalesOrderItem → Delivery → DeliveryItem → BillingDocument → BillingDocumentItem → JournalEntry → Payment
- **Supporting:** Customer, Product, Plant

**16 Relationship Types (Edges):**
- `ordered_by`, `has_item`, `for_product`, `produced_at`, `delivers_order`, `shipped_from`, `bills_order`, `billed_to`, `generates_entry`, `for_customer`, `paid_by`, `pays_invoice`

## 🤖 LLM Prompting Strategy & Pipeline

Our system employs a sophisticated Natural Language to SQL (NL → SQL) generation pipeline using **Google Gemini 2.0 Flash**. The strategy is designed to maximize accuracy and minimize hallucinations.

### NL → SQL Pipeline
1. **Schema-Aware System Prompt:** The LLM is injected with a highly compressed, token-optimized representation of the PostgreSQL schema. This includes all 19 table definitions, critical column types, and explicit relationship mappings (foreign keys) so the model understands how to JOIN tables effectively.
2. **Chain of Thought (CoT) Prompting:** We force the model to return a structured JSON response containing a `thinking` field, a `sql` field, and an `answer_template` field. By making the model "think aloud" and explain its JOIN strategy before writing the SQL, we drastically reduce syntax errors and hallucinated columns.
3. **Self-Correction Loop:** If the generated SQL fails execution against the database, the backend catches the PostgreSQL error (e.g., "column does not exist") and feeds it back to the LLM in a secondary prompt. The LLM acts as an autonomous agent, analyzing the error and attempting to fix its own query before returning a final response.
4. **Natural Language Answer Generation:** Raw SQL result rows are sent back to the LLM along with the user's original query. The LLM translates the tabular data into a polished, human-readable markdown response.

## 🛡️ Strict Guardrails

To ensure the system remains focused strictly on the domain of the provided SAP dataset and prevents prompt injection or expensive, unbounded queries, we implement a multi-layered guardrail architecture:

1. **Pre-filter Layer (Heuristic Filtering):** Before any API call is made to Gemini, the user's query is scrubbed against a predefined list of allowed domain keywords (e.g., "order", "delivery", "invoice", "plant") and banned patterns. If a query is clearly off-topic (e.g., "write me a poem" or "how to bake a cake"), it is rejected instantly.
2. **LLM-Level Refusal Directives:** The system prompt explicitly instructs the model with absolute rules: *"You are an SAP O2C data assistant. You MUST refuse to answer any questions unrelated to the provided schema. Do not answer general knowledge questions."*
3. **Read-Only SQL Execution Context:** All queries generated by the LLM are executed within a read-only transaction block. This prevents SQL injection attacks that attempt to `DROP`, `DELETE`, or `UPDATE` tables.
4. **Statement Timeout:** To prevent denial-of-service (DoS) via complex, long-running Cartesian products, PostgreSQL is configured with a strict statement timeout limit for LLM-generated queries.

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
