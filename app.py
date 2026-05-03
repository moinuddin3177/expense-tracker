"""
Streamlit web UI for the Monthly Expense Tracker.

Run:
    streamlit run app.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st

from tracker import Analysis, analyze, load_history, save_history

st.set_page_config(page_title="💳 Expense Tracker", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar — API key input (required when running as a bundled desktop app)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        help="Get your free key at console.anthropic.com",
        placeholder="sk-ant-...",
    )
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
    else:
        st.warning("Enter your API key to enable analysis.")

    st.divider()
    st.caption("Your key is used only for your own API calls and is never stored on disk.")

st.title("💳 Monthly Expense Tracker")
st.caption("Upload a bank or credit card statement (PDF, CSV, or TXT) to get an AI-powered spending breakdown and savings suggestions.")

tab_analyze, tab_trends = st.tabs(["📊 Analyze", "📈 Trends"])


# ---------------------------------------------------------------------------
# Tab 1 — Analyze
# ---------------------------------------------------------------------------

with tab_analyze:
    uploaded = st.file_uploader(
        "Drop your statement here",
        type=["pdf", "csv", "txt", "tsv"],
        help="PDF bank exports and CSV/TXT statements are both supported.",
    )

    if uploaded is not None:
        # Clear cached result when a new file is uploaded
        if st.session_state.get("last_filename") != uploaded.name:
            st.session_state.pop("analysis", None)
            st.session_state["last_filename"] = uploaded.name

        if "analysis" not in st.session_state:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                st.warning("Enter your Anthropic API key in the sidebar first.")
                st.stop()
            with st.spinner("Analyzing your statement with Claude…"):
                try:
                    result: Analysis = analyze(uploaded.read(), uploaded.name)
                    save_history(result)
                    st.session_state["analysis"] = result
                except Exception as exc:
                    st.error(f"Analysis failed: {exc}")
                    st.stop()

        analysis: Analysis = st.session_state["analysis"]

        # ── Header metrics ────────────────────────────────────────────────
        st.subheader(f"Results for {analysis.period}")
        col_total, col_cats, col_txns = st.columns(3)
        col_total.metric("Total Spent", f"${analysis.total_spent:,.2f}")
        col_cats.metric("Categories", len(analysis.categories))
        col_txns.metric(
            "Transactions",
            sum(c.transaction_count for c in analysis.categories),
        )

        st.write("")

        # ── Chart + table ─────────────────────────────────────────────────
        left, right = st.columns([1, 1])

        with left:
            df_cat = pd.DataFrame(
                [
                    {
                        "Category": f"{c.emoji} {c.name}",
                        "Spent ($)": c.total,
                        "% of Total": c.percentage,
                        "Transactions": c.transaction_count,
                    }
                    for c in sorted(analysis.categories, key=lambda x: x.total, reverse=True)
                ]
            )
            fig = px.pie(
                df_cat,
                names="Category",
                values="Spent ($)",
                hole=0.35,
                title="Spending by Category",
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

        with right:
            st.dataframe(
                df_cat.style.format({"Spent ($)": "${:.2f}", "% of Total": "{:.1f}%"}),
                use_container_width=True,
                hide_index=True,
            )

        # ── Summary ───────────────────────────────────────────────────────
        st.info(analysis.summary)

        # ── Suggestions ───────────────────────────────────────────────────
        st.subheader("💡 Where you can save")
        for concern in analysis.concerns:
            with st.expander(
                f"{concern.category} — {concern.reason}", expanded=True
            ):
                for s in concern.suggestions:
                    saving = f"~${s.estimated_monthly_saving}/mo"
                    st.markdown(f"- **{s.action}** &nbsp; `{saving}`")

    else:
        st.info("Upload a statement above to get started.")


# ---------------------------------------------------------------------------
# Tab 2 — Trends
# ---------------------------------------------------------------------------

with tab_trends:
    history = load_history()

    if len(history) < 1:
        st.info("No history yet. Analyze at least one statement in the Analyze tab.")
    else:
        # ── Monthly totals bar chart ───────────────────────────────────────
        df_totals = pd.DataFrame(
            [{"Period": a.period, "Total Spent ($)": a.total_spent} for a in history]
        )
        fig_bar = px.bar(
            df_totals,
            x="Period",
            y="Total Spent ($)",
            title="Monthly Spending Totals",
            text_auto=".2s",
        )
        fig_bar.update_layout(xaxis_title="", yaxis_title="Total Spent ($)")
        st.plotly_chart(fig_bar, use_container_width=True)

        if len(history) >= 2:
            # ── Category trends line chart ─────────────────────────────────
            rows = []
            for a in history:
                for c in a.categories:
                    rows.append(
                        {"Period": a.period, "Category": f"{c.emoji} {c.name}", "Spent ($)": c.total}
                    )
            df_lines = pd.DataFrame(rows)
            fig_line = px.line(
                df_lines,
                x="Period",
                y="Spent ($)",
                color="Category",
                markers=True,
                title="Category Spending Over Time",
            )
            fig_line.update_layout(xaxis_title="", legend_title="Category")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.caption("Upload a second month's statement to see category trends.")

        # ── Raw history table ─────────────────────────────────────────────
        with st.expander("Raw history data"):
            st.dataframe(df_totals, use_container_width=True, hide_index=True)
