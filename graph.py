"""
graph.py — LangGraph StateGraph definition.
Builds and compiles the sequential 6-agent pipeline.

Pipeline flow:
START → agent_1 → agent_2 → agent_3 → agent_4 → agent_5 → agent_6 → END
"""
from langgraph.graph import StateGraph, START, END
from state import CoverLetterState

# ── Import agent node functions ───────────────────────────────────────────────
from agents.agent_1_business_problem import node as agent_1_node
from agents.agent_2_cv_skills        import node as agent_2_node
from agents.agent_3_company_culture  import node as agent_3_node
from agents.agent_4_cover_points     import node as agent_4_node
from agents.agent_5_organise         import node as agent_5_node
from agents.agent_6_write_letter     import node as agent_6_node


def build_graph() -> StateGraph:
    """
    Construct and compile the LangGraph StateGraph.

    Returns:
        A compiled LangGraph application ready for .invoke() or .stream().
    """
    builder = StateGraph(CoverLetterState)

    # ── Register agent nodes ──────────────────────────────────────────────
    builder.add_node("agent_1", agent_1_node)
    builder.add_node("agent_2", agent_2_node)
    builder.add_node("agent_3", agent_3_node)
    builder.add_node("agent_4", agent_4_node)
    builder.add_node("agent_5", agent_5_node)
    builder.add_node("agent_6", agent_6_node)

    # ── Sequential edge chain ─────────────────────────────────────────────
    builder.add_edge(START,     "agent_1")
    builder.add_edge("agent_1", "agent_2")
    builder.add_edge("agent_2", "agent_3")
    builder.add_edge("agent_3", "agent_4")
    builder.add_edge("agent_4", "agent_5")
    builder.add_edge("agent_5", "agent_6")
    builder.add_edge("agent_6", END)

    return builder.compile()


# ── Module-level compiled graph (imported by ui.py) ───────────────────────────
graph = build_graph()
