"""
LLM service: Google Gemini integration for NL → SQL → data-backed answers.
Uses the new google-genai SDK with system_instruction to minimize token usage.
"""
import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
from database import execute_query_safe
from guardrails import is_domain_relevant

load_dotenv()

# Initialize the new Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.0-flash"

# Compact system instruction — sent as system_instruction, NOT as user message
# This uses far fewer tokens than the old chat-history approach
SYSTEM_INSTRUCTION = """You are a PostgreSQL data analyst for SAP Order-to-Cash data.

SCHEMA (use double quotes around all names):
sales_order_headers: sales_order, sales_order_type, sales_organization, distribution_channel, organization_division, sold_to_party, creation_date, total_net_amount, transaction_currency, overall_delivery_status, requested_delivery_date, customer_payment_terms
sales_order_items: sales_order, sales_order_item, material, requested_quantity, net_amount, transaction_currency, material_group, production_plant
outbound_delivery_headers: delivery_document, shipping_point, actual_goods_movement_date, creation_date, overall_goods_movement_status
outbound_delivery_items: delivery_document, delivery_document_item, plant, reference_sd_document, actual_delivery_quantity
billing_document_headers: billing_document, billing_document_type, billing_document_date, total_net_amount, transaction_currency, sold_to_party, accounting_document, company_code, fiscal_year, billing_document_is_cancelled
billing_document_items: billing_document, billing_document_item, material, billing_quantity, net_amount, reference_sd_document
journal_entry_items: company_code, fiscal_year, accounting_document, gl_account, reference_document, customer, amount_in_transaction_currency, posting_date, accounting_document_type
payments: company_code, fiscal_year, accounting_document, customer, invoice_reference, amount_in_transaction_currency, posting_date, sales_document
business_partners: business_partner, customer, business_partner_full_name, business_partner_name, industry, creation_date
business_partner_addresses: business_partner, city_name, country, postal_code, region
products: product, product_type, product_group, base_unit, gross_weight, net_weight, weight_unit
product_descriptions: product, language, product_description
plants: plant, plant_name, sales_organization, distribution_channel

JOINS: sold_to_party→business_partner, sales_order→sales_order, material→product, reference_sd_document→sales_order, delivery_document→delivery_document, billing_document→billing_document, accounting_document→accounting_document, reference_document→billing_document, invoice_reference→billing_document, customer→business_partner, sales_document→sales_order

ONLY answer O2C dataset questions. Refuse off-topic requests.
Return ONLY valid JSON: {"thinking":"...","sql":"SELECT ...","answer_template":"..."}
If unanswerable: {"thinking":"...","sql":null,"answer_template":"explanation"}
Use double quotes on all identifiers. Use PostgreSQL syntax."""


def call_gemini(prompt, max_retries=3):
    """Call Gemini with system instruction and retry on quota errors."""
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )
            return response.text.strip()
        except Exception as e:
            error_str = str(e).lower()
            print(f"  [LLM ERROR] Attempt {attempt+1}/{max_retries+1}: {type(e).__name__}: {str(e)[:200]}")

            # Check for rate limit / quota exhaustion (429)
            is_quota_error = any(kw in error_str for kw in [
                "quota", "rate", "resource_exhausted", "429", "too many requests"
            ])
            if is_quota_error:
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 15  # 15s, 30s, 45s
                    print(f"  [QUOTA] Retrying in {wait_time}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                return None  # All retries exhausted

            # Check for actual token limit errors
            is_token_error = any(kw in error_str for kw in [
                "token", "context_length", "max_tokens", "content_too_large"
            ])
            if is_token_error:
                print(f"  [TOKEN LIMIT] Actual token limit error detected")
                raise e  # Let caller handle with specific message

            raise e
    return None


def process_query(user_query: str, conversation_history: list = None) -> dict:
    """Process a natural language query: guardrails → LLM → SQL → answer."""
    # Step 1: Guardrail check
    is_relevant, rejection_msg = is_domain_relevant(user_query)
    if not is_relevant:
        return {"answer": rejection_msg, "sql": None, "results": None, "error": None}

    try:
        # Step 2: Ask LLM to generate SQL
        response_text = call_gemini(user_query)
        if response_text is None:
            return {
                "answer": "⏳ The Gemini API free-tier quota has been exceeded. "
                           "Please wait 1-2 minutes and try again, or check your API key quota at "
                           "https://aistudio.google.com/app/apikey",
                "sql": None, "results": None, "error": "quota",
            }

        # Parse JSON from response
        clean = response_text
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(lines[1:-1])

        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            return {"answer": response_text, "sql": None, "results": None, "error": None}

        sql = parsed.get("sql")
        thinking = parsed.get("thinking", "")
        answer_tmpl = parsed.get("answer_template", "")

        if not sql:
            return {"answer": answer_tmpl or thinking, "sql": None, "results": None, "error": None}

        # Step 3: Execute SQL
        results, error = execute_query_safe(sql, timeout_seconds=15)

        if error:
            # Auto-retry: ask LLM to fix the SQL
            fix_prompt = f"SQL error: {error}\nOriginal: {sql}\nQuestion: {user_query}\nFix it, same JSON."
            fix_text = call_gemini(fix_prompt)
            if fix_text:
                if fix_text.startswith("```"):
                    lines = fix_text.split("\n")
                    fix_text = "\n".join(lines[1:-1])
                try:
                    fix_parsed = json.loads(fix_text)
                    fix_sql = fix_parsed.get("sql")
                    if fix_sql:
                        results, error = execute_query_safe(fix_sql, timeout_seconds=15)
                        if not error:
                            sql = fix_sql
                except Exception:
                    pass

            if error:
                return {"answer": f"Query error: {error}", "sql": sql, "results": None, "error": error}

        # Step 4: Format answer from results
        if results is not None:
            display_results = results[:50]

            # Try LLM for natural language answer
            result_json = json.dumps(display_results, default=str)[:2000]
            answer_prompt = f"Question: {user_query}\nSQL results ({len(results)} rows): {result_json}\nAnswer naturally, be direct. No SQL. Use bullet points for lists."

            answer_text = call_gemini(answer_prompt)

            if answer_text is None:
                # Fallback: format results without LLM
                if len(display_results) <= 5:
                    answer_text = f"Found {len(results)} result(s):\n"
                    for r in display_results:
                        answer_text += "\n• " + ", ".join(f"**{k}**: {v}" for k, v in r.items())
                else:
                    answer_text = f"Query returned {len(results)} results. See the table below."

            return {"answer": answer_text, "sql": sql, "results": display_results, "error": None}

        return {"answer": "No results returned.", "sql": sql, "results": [], "error": None}

    except Exception as e:
        error_msg = str(e)
        error_lower = error_msg.lower()
        if "quota" in error_lower or "429" in error_lower or "resource_exhausted" in error_lower:
            return {
                "answer": "⏳ The Gemini API free-tier quota has been exceeded. "
                           "Please wait 1-2 minutes and try again, or check your API key quota at "
                           "https://aistudio.google.com/app/apikey",
                "sql": None, "results": None, "error": "quota",
            }
        if "token" in error_lower or "content_too_large" in error_lower:
            return {
                "answer": "⚠️ The prompt exceeded the model's token limit. Try a shorter or simpler question.",
                "sql": None, "results": None, "error": "token_limit",
            }
        return {"answer": f"Error: {error_msg}", "sql": None, "results": None, "error": error_msg}
