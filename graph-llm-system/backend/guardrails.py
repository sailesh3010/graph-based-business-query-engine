"""
Guardrails module: validates that user queries are relevant to the O2C dataset.
Rejects off-topic, general knowledge, creative writing, and irrelevant prompts.
"""

# Domain-relevant keywords (lowercase)
DOMAIN_KEYWORDS = {
    # Entity types
    "order", "orders", "sales order", "purchase order", "delivery", "deliveries",
    "billing", "invoice", "invoices", "payment", "payments", "journal", "entry",
    "customer", "customers", "product", "products", "material", "materials",
    "plant", "plants", "document", "documents",
    # O2C process terms
    "o2c", "order to cash", "order-to-cash", "shipped", "shipping", "billed",
    "delivered", "cancelled", "cancellation", "receivable", "accounts receivable",
    "sales", "revenue", "amount", "quantity", "flow", "trace", "track",
    # Data/analysis terms
    "highest", "lowest", "most", "least", "total", "count", "average", "sum",
    "broken", "incomplete", "missing", "status", "blocked", "overdue",
    "associated", "linked", "connected", "related", "relationship",
    # Specific SAP terms
    "sap", "company code", "fiscal year", "distribution channel", "sales organization",
    "profit center", "cost center", "gl account", "posting date", "net amount",
    "sold to party", "business partner", "accounting document", "reference document",
    # Graph terms
    "graph", "node", "nodes", "edge", "edges", "connection", "connections",
    "neighbor", "neighbors", "path", "network",
    # Query action words
    "find", "show", "list", "get", "which", "what", "how many", "how much",
    "identify", "trace", "compare", "analyze", "analyse", "breakdown",
}

# Off-topic patterns to reject
OFF_TOPIC_PATTERNS = [
    "write a poem", "write a story", "tell me a joke", "write me",
    "what is the meaning of life", "who is the president",
    "recipe", "weather", "sports", "movie", "music",
    "translate", "code this", "programming language",
    "who are you", "what are you", "your name",
    "capital of", "population of", "history of",
    "explain quantum", "explain relativity",
    "create a website", "build an app",
    "how to cook", "how to make",
]

REJECTION_MESSAGE = (
    "This system is designed to answer questions related to the Order-to-Cash "
    "dataset only. It covers sales orders, deliveries, billing documents, "
    "journal entries, payments, customers, products, and plants. "
    "Please ask a question about these entities or their relationships."
)


def is_domain_relevant(query: str) -> tuple[bool, str]:
    """
    Check if a query is relevant to the O2C dataset.
    Returns (is_relevant, rejection_reason).
    """
    query_lower = query.lower().strip()

    # Empty query
    if not query_lower or len(query_lower) < 3:
        return False, "Please enter a valid question about the dataset."

    # Check explicit off-topic patterns
    for pattern in OFF_TOPIC_PATTERNS:
        if pattern in query_lower:
            return False, REJECTION_MESSAGE

    # Check if any domain keywords are present
    has_domain_keyword = False
    for keyword in DOMAIN_KEYWORDS:
        if keyword in query_lower:
            has_domain_keyword = True
            break

    # If no domain keywords found, it's likely off-topic
    if not has_domain_keyword:
        # Give benefit of doubt to short queries that might be IDs
        if len(query_lower) < 15 and query_lower.replace(" ", "").isalnum():
            return True, ""  # Could be an entity ID lookup
        return False, REJECTION_MESSAGE

    return True, ""


def get_guardrail_system_prompt():
    """Return the guardrail instructions to embed in the LLM system prompt."""
    return """
IMPORTANT GUARDRAILS:
- You MUST only answer questions about the Order-to-Cash (O2C) dataset.
- The dataset contains: sales orders, sales order items, deliveries, delivery items,
  billing documents, billing document items, journal entries, payments,
  customers (business partners), products, and plants.
- If a user asks about anything unrelated to this dataset (general knowledge,
  creative writing, coding help, personal questions, etc.), respond with:
  "This system is designed to answer questions related to the provided dataset only."
- NEVER make up data. Only return information backed by actual query results.
- If a query returns no results, say so clearly.
"""
