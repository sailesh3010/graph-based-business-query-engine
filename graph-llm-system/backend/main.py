"""
FastAPI application: serves graph data and chat endpoints.
"""
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from database import get_schema_info, get_table_counts
from graph_builder import build_graph, graph_to_json, get_node_detail, get_neighbors
from llm_service import process_query

app = FastAPI(title="O2C Graph API", version="1.0.0")

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache the graph in memory
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        print("Building graph from database...")
        _graph = build_graph()
        print(f"Graph built: {_graph.number_of_nodes()} nodes, {_graph.number_of_edges()} edges")
    return _graph


# ─── Graph Endpoints ─────────────────────────────────────────

@app.get("/api/graph")
def api_get_graph():
    """Get the full graph as nodes and edges."""
    G = get_graph()
    return graph_to_json(G)


@app.get("/api/graph/node/{node_id:path}")
def api_get_node(node_id: str):
    """Get detailed metadata for a specific node."""
    G = get_graph()
    detail = get_node_detail(G, node_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return detail


@app.get("/api/graph/neighbors/{node_id:path}")
def api_get_neighbors(node_id: str, depth: int = 1):
    """Get the subgraph around a node."""
    G = get_graph()
    if not G.has_node(node_id):
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    depth = min(depth, 3)  # Cap depth to avoid huge subgraphs
    return get_neighbors(G, node_id, depth=depth)


@app.get("/api/graph/stats")
def api_graph_stats():
    """Get graph statistics."""
    G = get_graph()
    entity_counts = {}
    for _, data in G.nodes(data=True):
        entity = data.get("entity", "Unknown")
        entity_counts[entity] = entity_counts.get(entity, 0) + 1

    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "entity_counts": entity_counts,
    }


# ─── Chat Endpoint ───────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    conversation_history: Optional[list] = None


class ChatResponse(BaseModel):
    answer: str
    sql: Optional[str] = None
    results: Optional[list] = None
    error: Optional[str] = None


@app.post("/api/chat", response_model=ChatResponse)
def api_chat(request: ChatRequest):
    """Process a natural language query about the O2C dataset."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = process_query(request.query, request.conversation_history)
    return ChatResponse(**result)


# ─── Schema Endpoint ─────────────────────────────────────────

@app.get("/api/schema")
def api_schema():
    """Get the database schema information."""
    return {
        "schema": get_schema_info(),
        "counts": get_table_counts(),
    }


# ─── Health Check ────────────────────────────────────────────

@app.get("/api/health")
def api_health():
    return {"status": "ok", "message": "O2C Graph API is running"}


# ─── Static Frontend ─────────────────────────────────────────

# Serve the React app
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        # Return 404 for API routes, but return the React app for anything else
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return JSONResponse({"detail": "Not Found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
