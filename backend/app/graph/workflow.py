"""LangGraph: mood → context → coffee_profile → menu_blender → price_guardrail."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents import (
    coffee_profile_agent,
    context_agent,
    menu_blender_agent,
    mood_agent,
    price_guardrail_agent,
)
from app.graph.state import RecommendationState


def build_graph() -> StateGraph:
    graph = StateGraph(RecommendationState)

    graph.add_node("mood_agent", mood_agent.run)
    graph.add_node("context_agent", context_agent.run)
    graph.add_node("coffee_profile_agent", coffee_profile_agent.run)
    graph.add_node("menu_blender_agent", menu_blender_agent.run)
    graph.add_node("price_guardrail_agent", price_guardrail_agent.run)

    graph.add_edge(START, "mood_agent")
    graph.add_edge("mood_agent", "context_agent")
    graph.add_edge("context_agent", "coffee_profile_agent")
    graph.add_edge("coffee_profile_agent", "menu_blender_agent")
    graph.add_edge("menu_blender_agent", "price_guardrail_agent")
    graph.add_edge("price_guardrail_agent", END)

    return graph.compile()


recommendation_workflow = build_graph()
