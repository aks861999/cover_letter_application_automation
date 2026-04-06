"""
state.py — Shared TypedDict state schema for LangGraph StateGraph.
All 6 agents read from and write to this single state object.
"""
import operator
from typing import Annotated
from typing_extensions import TypedDict


class CoverLetterState(TypedDict):
    # ── User Inputs ──────────────────────────────────────────────────────────
    api_key: str                    # Gemini API key provided by user via UI
    # Under ── User Inputs ──, add after job_description:
    company_name: str   # Company name entered directly by user via UI
    run_output_dir: str 
    job_description: str            # Full job description pasted by user
    cv_selection: str          # ← ADD THIS — "cv_akash.md" or "cv_shreya.md"


    # ── Agent Outputs (saved as intermediate .md files) ───────────────────
    business_problem_md: str        # Agent 1: core business problem + how solved
    skills_cv_md: str               # Agent 2: CV with merged skills section
    culture_md: str                 # Agent 3: company vision & culture
    unorganised_points_md: str      # Agent 4: raw cover letter bullet points
    organised_sections_md: str      # Agent 5: points mapped to 4 paragraphs
    final_cover_letter_md: str      # Agent 6: the final written cover letter

    # ── Pipeline Metadata ────────────────────────────────────────────────
    # Annotated with operator.add so errors ACCUMULATE across agents (not overwrite)
    errors: Annotated[list[str], operator.add]
    current_agent: str              # Tracks which agent just completed
