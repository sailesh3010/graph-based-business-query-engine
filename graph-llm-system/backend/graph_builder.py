"""
Graph construction from PostgreSQL data using NetworkX.
Builds nodes for each entity type and edges from foreign key relationships.
"""
import networkx as nx
from database import execute_query


# Color palette for node types
NODE_COLORS = {
    "SalesOrder": "#4A90D9",
    "SalesOrderItem": "#6AB0E4",
    "Delivery": "#E67E22",
    "DeliveryItem": "#F0A04B",
    "BillingDocument": "#27AE60",
    "BillingDocumentItem": "#58D68D",
    "JournalEntry": "#8E44AD",
    "Payment": "#E74C3C",
    "Customer": "#F39C12",
    "Product": "#1ABC9C",
    "Plant": "#95A5A6",
}

# Node sizes by importance
NODE_SIZES = {
    "SalesOrder": 8,
    "SalesOrderItem": 4,
    "Delivery": 7,
    "DeliveryItem": 4,
    "BillingDocument": 7,
    "BillingDocumentItem": 4,
    "JournalEntry": 6,
    "Payment": 6,
    "Customer": 9,
    "Product": 6,
    "Plant": 5,
}


def build_graph():
    """Build the full Order-to-Cash graph from PostgreSQL data."""
    G = nx.Graph()

    # ─── 1. Load nodes ───────────────────────────────────────────
    # Sales Orders
    rows = execute_query("""
        SELECT sales_order, sales_order_type, sales_organization, 
               sold_to_party, total_net_amount, transaction_currency,
               overall_delivery_status, overall_ord_reltd_billg_status,
               creation_date, requested_delivery_date
        FROM sales_order_headers
    """)
    for r in rows:
        nid = f"SO:{r['sales_order']}"
        G.add_node(nid, entity="SalesOrder", label=r["sales_order"],
                   color=NODE_COLORS["SalesOrder"], size=NODE_SIZES["SalesOrder"], **r)

    # Sales Order Items
    rows = execute_query("""
        SELECT sales_order, sales_order_item, material, requested_quantity,
               net_amount, transaction_currency, production_plant, material_group
        FROM sales_order_items
    """)
    for r in rows:
        nid = f"SOI:{r['sales_order']}-{r['sales_order_item']}"
        G.add_node(nid, entity="SalesOrderItem", label=f"{r['sales_order']}/{r['sales_order_item']}",
                   color=NODE_COLORS["SalesOrderItem"], size=NODE_SIZES["SalesOrderItem"], **r)

    # Outbound Delivery Headers
    rows = execute_query("""
        SELECT delivery_document, shipping_point, actual_goods_movement_date,
               overall_goods_movement_status, overall_picking_status, creation_date
        FROM outbound_delivery_headers
    """)
    for r in rows:
        nid = f"DEL:{r['delivery_document']}"
        G.add_node(nid, entity="Delivery", label=r["delivery_document"],
                   color=NODE_COLORS["Delivery"], size=NODE_SIZES["Delivery"], **r)

    # Outbound Delivery Items
    rows = execute_query("""
        SELECT delivery_document, delivery_document_item, plant,
               reference_sd_document, reference_sd_document_item,
               actual_delivery_quantity, storage_location
        FROM outbound_delivery_items
    """)
    for r in rows:
        nid = f"DELI:{r['delivery_document']}-{r['delivery_document_item']}"
        G.add_node(nid, entity="DeliveryItem", label=f"{r['delivery_document']}/{r['delivery_document_item']}",
                   color=NODE_COLORS["DeliveryItem"], size=NODE_SIZES["DeliveryItem"], **r)

    # Billing Document Headers
    rows = execute_query("""
        SELECT billing_document, billing_document_type, total_net_amount,
               transaction_currency, sold_to_party, accounting_document,
               billing_document_date, billing_document_is_cancelled, company_code, fiscal_year
        FROM billing_document_headers
    """)
    for r in rows:
        nid = f"BILL:{r['billing_document']}"
        G.add_node(nid, entity="BillingDocument", label=r["billing_document"],
                   color=NODE_COLORS["BillingDocument"], size=NODE_SIZES["BillingDocument"], **r)

    # Billing Document Items
    rows = execute_query("""
        SELECT billing_document, billing_document_item, material,
               billing_quantity, net_amount, transaction_currency,
               reference_sd_document, reference_sd_document_item
        FROM billing_document_items
    """)
    for r in rows:
        nid = f"BILI:{r['billing_document']}-{r['billing_document_item']}"
        G.add_node(nid, entity="BillingDocumentItem", label=f"{r['billing_document']}/{r['billing_document_item']}",
                   color=NODE_COLORS["BillingDocumentItem"], size=NODE_SIZES["BillingDocumentItem"], **r)

    # Journal Entry Items
    rows = execute_query("""
        SELECT company_code, fiscal_year, accounting_document, gl_account,
               reference_document, customer, transaction_currency,
               amount_in_transaction_currency, posting_date, document_date,
               accounting_document_type, accounting_document_item
        FROM journal_entry_items
    """)
    for r in rows:
        nid = f"JE:{r['accounting_document']}-{r['accounting_document_item']}"
        G.add_node(nid, entity="JournalEntry", label=f"{r['accounting_document']}",
                   color=NODE_COLORS["JournalEntry"], size=NODE_SIZES["JournalEntry"], **r)

    # Payments
    rows = execute_query("""
        SELECT company_code, fiscal_year, accounting_document, accounting_document_item,
               customer, invoice_reference, amount_in_transaction_currency,
               transaction_currency, posting_date, sales_document
        FROM payments
    """)
    for r in rows:
        nid = f"PAY:{r['accounting_document']}-{r['accounting_document_item']}"
        G.add_node(nid, entity="Payment", label=f"{r['accounting_document']}",
                   color=NODE_COLORS["Payment"], size=NODE_SIZES["Payment"], **r)

    # Business Partners (Customers)
    rows = execute_query("""
        SELECT business_partner, customer, business_partner_full_name,
               business_partner_name, correspondence_language, industry,
               creation_date
        FROM business_partners
    """)
    for r in rows:
        nid = f"CUST:{r['business_partner']}"
        G.add_node(nid, entity="Customer", label=r.get("business_partner_name") or r["business_partner"],
                   color=NODE_COLORS["Customer"], size=NODE_SIZES["Customer"], **r)

    # Products
    rows = execute_query("""
        SELECT p.product, p.product_type, p.product_group, p.base_unit,
               p.gross_weight, p.net_weight, p.weight_unit, p.division,
               pd.product_description
        FROM products p
        LEFT JOIN product_descriptions pd ON p.product = pd.product AND pd.language = 'EN'
    """)
    for r in rows:
        nid = f"PROD:{r['product']}"
        G.add_node(nid, entity="Product", label=r.get("product_description") or r["product"],
                   color=NODE_COLORS["Product"], size=NODE_SIZES["Product"], **r)

    # Plants
    rows = execute_query("""
        SELECT plant, plant_name, sales_organization, distribution_channel
        FROM plants
    """)
    for r in rows:
        nid = f"PLANT:{r['plant']}"
        G.add_node(nid, entity="Plant", label=r.get("plant_name") or r["plant"],
                   color=NODE_COLORS["Plant"], size=NODE_SIZES["Plant"], **r)

    # ─── 2. Build edges ───────────────────────────────────────────
    # SalesOrder → Customer
    for r in execute_query("SELECT sales_order, sold_to_party FROM sales_order_headers WHERE sold_to_party IS NOT NULL"):
        src = f"SO:{r['sales_order']}"
        tgt = f"CUST:{r['sold_to_party']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="ordered_by")

    # SalesOrder → SalesOrderItem
    for r in execute_query("SELECT DISTINCT sales_order, sales_order_item FROM sales_order_items"):
        src = f"SO:{r['sales_order']}"
        tgt = f"SOI:{r['sales_order']}-{r['sales_order_item']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="has_item")

    # SalesOrderItem → Product
    for r in execute_query("SELECT sales_order, sales_order_item, material FROM sales_order_items WHERE material IS NOT NULL"):
        src = f"SOI:{r['sales_order']}-{r['sales_order_item']}"
        tgt = f"PROD:{r['material']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="for_product")

    # SalesOrderItem → Plant
    for r in execute_query("SELECT sales_order, sales_order_item, production_plant FROM sales_order_items WHERE production_plant IS NOT NULL"):
        src = f"SOI:{r['sales_order']}-{r['sales_order_item']}"
        tgt = f"PLANT:{r['production_plant']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="produced_at")

    # Delivery → DeliveryItem
    for r in execute_query("SELECT DISTINCT delivery_document, delivery_document_item FROM outbound_delivery_items"):
        src = f"DEL:{r['delivery_document']}"
        tgt = f"DELI:{r['delivery_document']}-{r['delivery_document_item']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="has_item")

    # DeliveryItem → SalesOrder (via reference_sd_document)
    for r in execute_query("SELECT delivery_document, delivery_document_item, reference_sd_document FROM outbound_delivery_items WHERE reference_sd_document IS NOT NULL"):
        src = f"DELI:{r['delivery_document']}-{r['delivery_document_item']}"
        tgt = f"SO:{r['reference_sd_document']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="delivers_order")

    # DeliveryItem → Plant
    for r in execute_query("SELECT delivery_document, delivery_document_item, plant FROM outbound_delivery_items WHERE plant IS NOT NULL"):
        src = f"DELI:{r['delivery_document']}-{r['delivery_document_item']}"
        tgt = f"PLANT:{r['plant']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="shipped_from")

    # BillingDocument → BillingDocumentItem
    for r in execute_query("SELECT DISTINCT billing_document, billing_document_item FROM billing_document_items"):
        src = f"BILL:{r['billing_document']}"
        tgt = f"BILI:{r['billing_document']}-{r['billing_document_item']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="has_item")

    # BillingDocumentItem → SalesOrder (via reference_sd_document)
    for r in execute_query("SELECT billing_document, billing_document_item, reference_sd_document FROM billing_document_items WHERE reference_sd_document IS NOT NULL"):
        src = f"BILI:{r['billing_document']}-{r['billing_document_item']}"
        tgt = f"SO:{r['reference_sd_document']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="bills_order")

    # BillingDocumentItem → Product
    for r in execute_query("SELECT billing_document, billing_document_item, material FROM billing_document_items WHERE material IS NOT NULL"):
        src = f"BILI:{r['billing_document']}-{r['billing_document_item']}"
        tgt = f"PROD:{r['material']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="for_product")

    # BillingDocument → Customer
    for r in execute_query("SELECT billing_document, sold_to_party FROM billing_document_headers WHERE sold_to_party IS NOT NULL"):
        src = f"BILL:{r['billing_document']}"
        tgt = f"CUST:{r['sold_to_party']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="billed_to")

    # BillingDocument → JournalEntry (via accounting_document)
    for r in execute_query("""
        SELECT DISTINCT bh.billing_document, je.accounting_document, je.accounting_document_item
        FROM billing_document_headers bh
        JOIN journal_entry_items je ON bh.accounting_document = je.accounting_document
        WHERE bh.accounting_document IS NOT NULL
    """):
        src = f"BILL:{r['billing_document']}"
        tgt = f"JE:{r['accounting_document']}-{r['accounting_document_item']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="generates_entry")

    # JournalEntry → Customer
    for r in execute_query("SELECT DISTINCT accounting_document, accounting_document_item, customer FROM journal_entry_items WHERE customer IS NOT NULL"):
        src = f"JE:{r['accounting_document']}-{r['accounting_document_item']}"
        tgt = f"CUST:{r['customer']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="for_customer")

    # Payment → Customer
    for r in execute_query("SELECT DISTINCT accounting_document, accounting_document_item, customer FROM payments WHERE customer IS NOT NULL"):
        src = f"PAY:{r['accounting_document']}-{r['accounting_document_item']}"
        tgt = f"CUST:{r['customer']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="paid_by")

    # Payment → BillingDocument (via invoice_reference)
    for r in execute_query("SELECT accounting_document, accounting_document_item, invoice_reference FROM payments WHERE invoice_reference IS NOT NULL"):
        src = f"PAY:{r['accounting_document']}-{r['accounting_document_item']}"
        tgt = f"BILL:{r['invoice_reference']}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, relation="pays_invoice")

    return G


def graph_to_json(G):
    """Convert the NetworkX graph to a JSON-serializable dict for the frontend."""
    nodes = []
    for nid, data in G.nodes(data=True):
        node = {"id": nid, **data}
        # Convert non-serializable values to strings
        for k, v in node.items():
            if v is not None and not isinstance(v, (str, int, float, bool)):
                node[k] = str(v)
        nodes.append(node)

    edges = []
    for src, tgt, data in G.edges(data=True):
        edges.append({
            "source": src,
            "target": tgt,
            "relation": data.get("relation", "related"),
        })

    return {"nodes": nodes, "edges": edges}


def get_node_detail(G, node_id):
    """Get all metadata for a specific node."""
    if not G.has_node(node_id):
        return None
    data = dict(G.nodes[node_id])
    neighbors = list(G.neighbors(node_id))
    data["connections"] = len(neighbors)
    data["neighbor_ids"] = neighbors[:50]  # Cap at 50
    return data


def get_neighbors(G, node_id, depth=1):
    """Get subgraph around a node up to given depth."""
    if not G.has_node(node_id):
        return {"nodes": [], "edges": []}

    # BFS to find neighbors within depth
    visited = {node_id}
    frontier = {node_id}
    for _ in range(depth):
        next_frontier = set()
        for n in frontier:
            for neighbor in G.neighbors(n):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier

    subgraph = G.subgraph(visited)
    return graph_to_json(subgraph)
