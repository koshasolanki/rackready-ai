"""Shared UI helpers for RackReady AI."""
from __future__ import annotations

import pandas as pd
import streamlit as st

GREEN = "#76B900"
GREY = "#8A8F98"
AMBER = "#F2A900"


def money(x) -> str:
    if x is None:
        return "n/a"
    a = abs(x)
    if a >= 1e9:
        return f"${x/1e9:,.2f}B"
    if a >= 1e6:
        return f"${x/1e6:,.1f}M"
    if a >= 1e3:
        return f"${x/1e3:,.0f}K"
    return f"${x:,.0f}"


def yrs(x):
    return "n/a" if x is None else f"{x:.1f} yrs"


def usd_table(df: pd.DataFrame, cols: list[str]):
    return df.style.format({c: "${:,.0f}" for c in cols})


def metric(col, label, value, delta=None, delta_color="off"):
    esc = lambda t: None if t is None else str(t).replace("$", "\\$")
    kw = dict(delta=esc(delta), delta_color=delta_color)
    if delta_color == "off":
        kw["delta_arrow"] = "off"
    try:
        col.metric(label, esc(value), **kw)
    except TypeError:
        kw.pop("delta_arrow", None)
        col.metric(label, esc(value), **kw)


def esc_md(t: str) -> str:
    return str(t).replace("\\$", "$").replace("$", "\\$")


def df_md(df: pd.DataFrame, money_cols=()) -> str:
    d = df.copy()
    for c in money_cols:
        d[c] = d[c].map(lambda v: f"${v:,.0f}")
    return d.to_markdown(index=False)


def dark(fig, height=360, **kw):
    fig.update_layout(template="plotly_dark", height=height, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.12), paper_bgcolor="rgba(0,0,0,0)", **kw)
    return fig
