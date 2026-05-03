"""
Core analysis logic for the Expense Tracker web app.
Handles statement parsing, Claude API calls, and history persistence.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Pydantic response schema
# ---------------------------------------------------------------------------

class Suggestion(BaseModel):
    action: str
    estimated_monthly_saving: int  # USD


class Concern(BaseModel):
    category: str
    reason: str
    suggestions: list[Suggestion]


class CategoryBreakdown(BaseModel):
    name: str
    emoji: str
    total: float
    percentage: float
    transaction_count: int


class Analysis(BaseModel):
    period: str           # e.g. "April 2025"
    total_spent: float
    categories: list[CategoryBreakdown]
    concerns: list[Concern]  # top 3
    summary: str


# ---------------------------------------------------------------------------
# System prompt (cached)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert personal finance advisor. Analyze the provided bank or \
credit card statement and return a structured JSON response.

CATEGORIES — map every transaction to exactly one:
  Housing       (🏠) — rent, mortgage, utilities, home repairs
  Food & Dining (🍔) — groceries, restaurants, takeout, coffee shops
  Transportation(🚗) — gas, parking, rideshare, car payment, public transit
  Entertainment (🎬) — streaming, movies, concerts, games, hobbies
  Shopping      (🛍️) — clothing, electronics, household goods, online orders
  Healthcare    (💊) — pharmacy, doctors, dentist, health/vision insurance
  Personal Care (💅) — gym, salon, beauty, grooming
  Travel        (✈️) — flights, hotels, vacation spending
  Subscriptions (📱) — software, apps, memberships, recurring services
  Financial     (💰) — savings transfers, investments, loan payments, bank fees
  Other         (❓) — anything that doesn't fit above

Ignore non-spending rows: opening balance, closing balance, salary deposits, \
credits, refunds.

Return a JSON object matching this schema exactly:
{
  "period": "<Month Year, e.g. April 2025>",
  "total_spent": <float — sum of all debits>,
  "categories": [
    {
      "name": "<category name without emoji>",
      "emoji": "<single emoji>",
      "total": <float>,
      "percentage": <float — 0-100>,
      "transaction_count": <int>
    }
  ],
  "concerns": [
    {
      "category": "<category name>",
      "reason": "<why this category warrants attention>",
      "suggestions": [
        {
          "action": "<specific, actionable recommendation>",
          "estimated_monthly_saving": <int — USD>
        }
      ]
    }
  ],
  "summary": "<2-3 sentence encouraging overview of the month>"
}

Include only categories that have at least one transaction.
concerns must contain exactly 3 entries (the top categories by spend weighted \
against typical budgets).
Each concern must have 2-3 suggestions.
"""


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(file_bytes: bytes, filename: str) -> Analysis:
    """Send a statement to Claude and return a structured Analysis."""
    client = anthropic.Anthropic()
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
        content: list = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": b64,
                },
            },
            {"type": "text", "text": "Analyze this statement and return the JSON."},
        ]
    else:
        raw = file_bytes.decode("utf-8", errors="replace")
        content = [
            {
                "type": "text",
                "text": (
                    f"Here is my bank statement:\n\n```\n{raw}\n```\n\n"
                    "Analyze it and return the JSON."
                ),
            }
        ]

    response = client.messages.parse(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": content}],
        output_format=Analysis,
    )
    return response.parsed


# ---------------------------------------------------------------------------
# History persistence
# ---------------------------------------------------------------------------

# When frozen by PyInstaller, store history next to the .exe so it survives
# between runs (sys._MEIPASS is a temp dir that's recreated each launch).
if getattr(sys, "frozen", False):
    HISTORY_DIR = Path(sys.executable).parent / "history"
else:
    HISTORY_DIR = Path("history")


def save_history(analysis: Analysis) -> None:
    HISTORY_DIR.mkdir(exist_ok=True)
    safe_name = analysis.period.replace(" ", "_")
    path = HISTORY_DIR / f"{safe_name}.json"
    path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")


def load_history() -> list[Analysis]:
    if not HISTORY_DIR.exists():
        return []
    analyses = []
    for p in sorted(HISTORY_DIR.glob("*.json")):
        try:
            analyses.append(Analysis.model_validate_json(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return analyses
