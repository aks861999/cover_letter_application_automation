"""
Agent 4 — Cover Letter Points Generator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No web search. Pure synthesis task.
Prompt reconstructed from user's raw notes using CRISPE framework.

Task  : Synthesise all research + CV into RAW bullet-point ideas for
        the cover letter — across 5 dimensions.
        WARNING: Does NOT write the cover letter itself.
Input : business_problem_md, culture_md, skills_cv_md (from state)
Output: unorganised_cover_letter_content.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import sys
from pathlib import Path
from utils import generate_with_retry, MaxRetriesExceeded

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from google import genai
from google.genai import types
from state import CoverLetterState
from prompts.agent_4 import SYSTEM_PROMPT

OUTPUT_FILE = _ROOT / "outputs" / "unorganised_cover_letter_content.md"



def run(
    api_key: str,
    business_problem_md: str,
    culture_md: str,
    skills_cv_md: str,
    output_dir: Path) -> str:

    """
    Execute Agent 4: generate raw cover letter bullet-point material.

    Args:
        api_key: Gemini API key.
        business_problem_md: Agent 1 output.
        culture_md: Agent 3 output.
        skills_cv_md: Agent 2 output (CV with skills).

    Returns:
        Markdown string with raw bullet-point ideas across 5 dimensions.
    """
    out_file = output_dir / "unorganised_cover_letter_content.md"  # agent-specific name

    client = genai.Client(api_key=api_key)

    user_message = (
        "---BUSINESS PROBLEM DOCUMENT START---\n"
        f"{business_problem_md}\n"
        "---BUSINESS PROBLEM DOCUMENT END---\n\n"
        "---COMPANY VISION & CULTURE DOCUMENT START---\n"
        f"{culture_md}\n"
        "---COMPANY VISION & CULTURE DOCUMENT END---\n\n"
        "---CANDIDATE CV WITH SKILLS START---\n"
        f"{skills_cv_md}\n"
        "---CANDIDATE CV WITH SKILLS END---\n\n"
        "Now analyse all three documents and generate raw bullet-point material for all 5 dimensions.\n"
        "Remember: Do NOT write the cover letter. Only raw ideas and specific, concrete points.\n"
        "Reference actual content from the documents above — no generic advice."
    )

    response = generate_with_retry(
        client,
        model="gemini-3-flash-preview",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=8192,
        ),
    )

    result = response.text
    out_file.write_text(result, encoding="utf-8")

    return result


# ── LangGraph Node Wrapper ────────────────────────────────────────────────────
def node(state: CoverLetterState) -> dict:
    try:
        output_dir = Path(state["run_output_dir"])
        result = run(
            state["api_key"],
            state["business_problem_md"],
            state["culture_md"],
            state["skills_cv_md"],
            output_dir
        )
        
        return {
            "unorganised_points_md": result,
            "current_agent": "agent_4_complete",
        }
    except Exception as exc:             # ← catches everything including MaxRetriesExceeded
        raise RuntimeError(
            f"Agent 4 failed — pipeline stopped: {exc}"
        ) from exc