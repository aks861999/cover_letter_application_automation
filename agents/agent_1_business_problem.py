"""
Agent 1 — Business Problem Research
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mandatory web search (GoogleSearch grounding via Gemini API).

Task  : Find the core business problem the company wants to solve,
        specifically aligned with the JD, and how they actually solved it.
Input : job_description (from state)
Output: The_Core_Business_Problem_and_how_it_was_solved.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import sys
from pathlib import Path
from utils import generate_with_retry, MaxRetriesExceeded
from prompts.agent_1 import SYSTEM_PROMPT


# ── Ensure project root is on sys.path so `state` can be imported ──────
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from google import genai
from google.genai import types
from state import CoverLetterState

OUTPUT_FILE = _ROOT / "outputs" / "The_Core_Business_Problem_and_how_it_was_solved.md"




def run(api_key: str, job_description: str, output_dir: Path) -> str:

    """
    Execute Agent 1: research the core business problem with mandatory web search.

    Args:
        api_key: Gemini API key from the user.
        job_description: Full text of the job description.

    Returns:
        Markdown string with the research findings.
    """
    out_file = output_dir / "The_Core_Business_Problem_and_how_it_was_solved.md" 

    client = genai.Client(api_key=api_key)

    user_message = (
        "---JOB DESCRIPTION START---\n"
        f"{job_description}\n"
        "---JOB DESCRIPTION END---\n\n"
        "Now execute your research following all mandatory constraints and the search strategy.\n"
        "Do NOT generate your response until you have performed at least 3 web searches from different angles.\n"
        "Think step by step: first identify the company and role, then search, then synthesise."
    )

    response = generate_with_retry(
        client,
        model="gemini-2.5-flash",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=1.0,          # Required for search-grounded generation
            max_output_tokens=8192,
        ),
    )

    result = response.text
    out_file.write_text(result, encoding="utf-8")
    return result


# ── LangGraph Node Wrapper ────────────────────────────────────────────────────
def node(state: CoverLetterState) -> dict:
    """LangGraph node — wraps run() and returns state update dict."""
    try:
        output_dir = Path(state["run_output_dir"])
        result = run(state["api_key"], state["job_description"], output_dir)
        return {
            "business_problem_md": result,
            "current_agent": "agent_1_complete",
        }
    except Exception as exc:             # ← catches everything including MaxRetriesExceeded
        raise RuntimeError(
            f"Agent 1 failed — pipeline stopped: {exc}"
        ) from exc


