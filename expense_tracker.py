#!/usr/bin/env python3
"""
Monthly Expense Tracker
Uploads a bank/credit card statement (PDF or CSV/TXT), categorizes spending,
and suggests where to cut back.

Usage:
    python expense_tracker.py statement.pdf
    python expense_tracker.py statement.csv
"""

import sys
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# System prompt — cached so repeated runs skip re-tokenizing it
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are an expert personal finance advisor. When given a bank or credit card \
statement, analyze it in three steps:

STEP 1 — CATEGORIZE
Map every transaction to exactly one category:
  • 🏠 Housing       — rent, mortgage, utilities, home repairs
  • 🍔 Food & Dining — groceries, restaurants, takeout, coffee shops
  • 🚗 Transportation — gas, parking, rideshare, car payment, public transit
  • 🎬 Entertainment — streaming, movies, concerts, games, hobbies
  • 🛍️ Shopping       — clothing, electronics, household goods, online orders
  • 💊 Healthcare     — pharmacy, doctors, dentist, health/vision insurance
  • 💅 Personal Care  — gym, salon, beauty, grooming
  • ✈️ Travel         — flights, hotels, vacation spending
  • 📱 Subscriptions  — software, apps, memberships, recurring services
  • 💰 Financial      — savings transfers, investments, loan payments, bank fees
  • ❓ Other          — anything that doesn't fit above

Ignore non-spending rows (opening balance, closing balance, payments received, \
refunds unless they offset a spend category).

STEP 2 — SUMMARIZE
Present a table with columns: Category | Total Spent | % of Total | # Transactions
Then state the grand total for the period.

STEP 3 — SUGGEST
Pick the 3 categories with the highest spend (weighted against typical budgets, \
not just absolute amount). For each, give 2–3 specific, actionable recommendations \
with a rough estimated monthly saving (e.g. "Cancel unused gym membership: ~$50/mo").

Keep the tone encouraging and practical — one concrete next step per suggestion.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stream_analysis(
    client: anthropic.Anthropic,
    messages: list,
    *,
    use_beta: bool = False,
    betas: list[str] | None = None,
) -> None:
    """Stream the analysis to stdout, using beta namespace only when needed."""
    kwargs = dict(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    )

    if use_beta:
        kwargs["betas"] = betas or []
        stream_ctx = client.beta.messages.stream(**kwargs)
    else:
        stream_ctx = client.messages.stream(**kwargs)

    with stream_ctx as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)


# ---------------------------------------------------------------------------
# Per-format handlers
# ---------------------------------------------------------------------------

def _analyze_pdf(client: anthropic.Anthropic, path: Path) -> None:
    print("📤 Uploading statement…")
    with open(path, "rb") as f:
        uploaded = client.beta.files.upload(
            file=(path.name, f, "application/pdf"),
        )
    file_id = uploaded.id
    print(f"✅ Uploaded  (id: {file_id})\n{'─' * 65}")

    try:
        _stream_analysis(
            client,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "file", "file_id": file_id},
                        },
                        {
                            "type": "text",
                            "text": "Please analyze this statement following the three steps.",
                        },
                    ],
                }
            ],
            use_beta=True,
            betas=["files-api-2025-04-14"],
        )
    finally:
        client.beta.files.delete(file_id)
        print(f"\n{'─' * 65}\n🗑  Temporary file removed from Anthropic servers.")


def _analyze_text(client: anthropic.Anthropic, path: Path) -> None:
    print(f"📖 Reading {path.name}…\n{'─' * 65}")
    raw = path.read_text(encoding="utf-8", errors="replace")

    _stream_analysis(
        client,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Here is my statement:\n\n```\n{raw}\n```\n\n"
                    "Please analyze it following the three steps."
                ),
            }
        ],
    )
    print(f"\n{'─' * 65}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def analyze_statement(file_path: str) -> None:
    client = anthropic.Anthropic()
    path = Path(file_path)

    if not path.exists():
        print(f"❌  File not found: {file_path}")
        sys.exit(1)

    suffix = path.suffix.lower()
    print(f"\n💳  Monthly Expense Tracker")
    print(f"    File : {path.name}")

    if suffix == ".pdf":
        _analyze_pdf(client, path)
    elif suffix in (".csv", ".txt", ".tsv"):
        _analyze_text(client, path)
    else:
        print(
            f"❌  Unsupported format '{suffix}'.\n"
            "    Accepted: .pdf  .csv  .txt  .tsv"
        )
        sys.exit(1)

    print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python expense_tracker.py <statement>")
        print("       Supported formats: PDF, CSV, TXT, TSV")
        sys.exit(1)

    analyze_statement(sys.argv[1])
