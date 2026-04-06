"""
Agent 6 — Cover Letter Writer (with Self-Critique Loop)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No web search. Final generation task.
Implements a two-pass self-critique loop to enforce all writing constraints.

Task  : Write the final cover letter from the organised sections.
        After first draft → run self-critique → regenerate if violations found.
Input : organised_sections_md (from state, Agent 5 output)
Output: final_cover_letter.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import json
import sys
from pathlib import Path
from utils import generate_with_retry, MaxRetriesExceeded

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from google import genai
from google.genai import types
from state import CoverLetterState
from prompts.agent_6 import CRITIQUE_SYSTEM_PROMPT, WRITER_SYSTEM_PROMPT   


from pydantic import BaseModel, field_validator
from typing import Optional

class CritiqueResult(BaseModel):
    has_violations:       bool
    consecutive_i_starts: bool = False   # default False — older responses won't have it
    violations:           list[str]
    approved:             Optional[bool] = None

    @field_validator("violations", mode="before")
    @classmethod
    def coerce_violations(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v






def _write_letter(client: genai.Client, organised_sections_md: str) -> str:
    """First pass: generate the cover letter from organised sections."""
    response = generate_with_retry(
        client,
        model="gemini-3-flash-preview",
        contents=(
            "---ORGANISED COVER LETTER SECTIONS START---\n"
            f"{organised_sections_md}\n"
            "---ORGANISED COVER LETTER SECTIONS END---\n\n"
            "Write the cover letter now based on the content in these sections.\n"
            "Follow all writing rules and the 5-paragraph structure strictly.\n"
            "Use only the content provided — do not invent facts not present in the sections."
        ),
        config=types.GenerateContentConfig(
            system_instruction=WRITER_SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=8192,
        ),
    )
    # ── Truncation guard ─────────────────────────────────────────────────
    candidate = response.candidates[0]
    if candidate.finish_reason.name == "MAX_TOKENS":
        raise RuntimeError(
            "Cover letter was truncated at token limit — "
            "increase max_output_tokens or shorten the input sections."
        )
    # ─────────────────────────────────────────────────────────────────────
    return response.text


def _critique_letter(client: genai.Client, letter: str) -> dict:
    """Second pass: audit the draft for constraint violations."""
    response = generate_with_retry(
        client,
        model="gemini-3-flash-preview",
        contents=(
            "---COVER LETTER TO AUDIT START---\n"
            f"{letter}\n"
            "---COVER LETTER TO AUDIT END---\n\n"
            "Audit this cover letter against all constraints. Return the JSON object only."
        ),
        config=types.GenerateContentConfig(
            system_instruction=CRITIQUE_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=1024,
        ),
    )
     # ── Truncation guard ─────────────────────────────────────────────────
    candidate = response.candidates[0]
    if candidate.finish_reason.name == "MAX_TOKENS":
        raise RuntimeError(
            "Cover letter was truncated at token limit — "
            "increase max_output_tokens or shorten the input sections."
        )
    # ─────────────────────────────────────────────────────────────────────
    try:
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1]).strip()
        data = json.loads(raw)
        validated = CritiqueResult(**data)
        return validated.model_dump()
    except (json.JSONDecodeError, ValueError):
        return {"has_violations": False, "consecutive_i_starts": False,
                "violations": [], "approved": None}



def _regenerate_with_feedback(
    client: genai.Client,
    organised_sections_md: str,
    draft: str,
    violations: list[str],
) -> str:
    """Third pass: regenerate fixing the specific violations identified."""
    violations_text = "\n".join(f"  - {v}" for v in violations)

    response = generate_with_retry(
        client,
        model="gemini-3-flash-preview",
        contents=(
            "---ORGANISED COVER LETTER SECTIONS START---\n"
            f"{organised_sections_md}\n"
            "---ORGANISED COVER LETTER SECTIONS END---\n\n"
            "---PREVIOUS DRAFT (CONTAINS VIOLATIONS) START---\n"
            f"{draft}\n"
            "---PREVIOUS DRAFT END---\n\n"
            "VIOLATIONS THAT MUST BE FIXED IN THE REWRITE:\n"
            f"{violations_text}\n\n"
            "Rewrite the cover letter, fixing ALL violations listed above.\n"
            "Keep the same content and structure. Only fix the violations.\n"
            "Follow all writing rules strictly."
        ),
        config=types.GenerateContentConfig(
            system_instruction=WRITER_SYSTEM_PROMPT,
            temperature=0.6,
            max_output_tokens=8192,
        ),
    )
    return response.text


def run(api_key: str, organised_sections_md: str, output_dir: Path) -> str:
    """
    Execute Agent 6: write the final cover letter with self-critique loop.

    Args:
        api_key: Gemini API key.
        organised_sections_md: Agent 5 output (4 sections of organised bullet points).

    Returns:
        The final polished cover letter as a string.
    """
    out_file = output_dir / "final_cover_letter.md"  # agent-specific name

    client = genai.Client(api_key=api_key)

    # Pass 1 — Initial draft
    letter = _write_letter(client, organised_sections_md)

    # Pass 2 — Self-critique
    critique = _critique_letter(client, letter)
    if critique.get("approved") is None:
        print("⚠️  Agent 6: critique call failed — skipping regeneration, using first draft.")

    # Pass 3 — Regenerate if violations found (conditional LangGraph edge pattern)
    if critique.get("has_violations") and critique.get("violations"):
        letter = _regenerate_with_feedback(
            client,
            organised_sections_md,
            letter,
            critique["violations"],
        )

    out_file.write_text(letter, encoding="utf-8")    
    return letter


# ── LangGraph Node Wrapper ────────────────────────────────────────────────────
def node(state: CoverLetterState) -> dict:
    try:
        result = run(state["api_key"], state["organised_sections_md"], Path(state["run_output_dir"]))
        return {
            "final_cover_letter_md": result,
            "current_agent": "agent_6_complete",
        }
    except Exception as exc:             # ← catches everything including MaxRetriesExceeded
        raise RuntimeError(
            f"Agent X failed — pipeline stopped: {exc}"
        ) from exc
