"""Builds the LangGraph StateGraph from config/graph.yaml."""
from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Callable

from langgraph.graph import END, StateGraph

from app.config import settings
from app.state import SupportState


def _resolve(dotted: str) -> Callable:
    """Turn a 'package.module:function' string into the actual callable."""
    module_path, _, func_name = dotted.partition(":")
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


@lru_cache(maxsize=1)
def build_graph():
    spec = settings.graph
    workflow = StateGraph(SupportState)

    for name, dotted in spec["nodes"].items():
        workflow.add_node(name, _resolve(dotted))

    workflow.set_entry_point(spec["entry_point"])

    for src, dst in spec.get("edges", []):
        workflow.add_edge(src, dst)

    for cond in spec.get("conditional_edges", []):
        router = _resolve(cond["router"])
        workflow.add_conditional_edges(cond["source"], router, cond["mapping"])

    for name in spec.get("finish", []):
        workflow.add_edge(name, END)

    return workflow.compile()
