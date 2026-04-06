"""
Agent 5 — Content Organiser
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No web search. Pure structuring task.
Uses response_mime_type="application/json" to force structured output.

Task  : Redistribute existing bullet points (from Agent 4) into the
        4 cover letter sections WITHOUT adding new content.
Input : unorganised_points_md (from state)
Output: super_organised_content_for_cover_letter.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from google import genai
from google.genai import types
from state import CoverLetterState
from utils import generate_with_retry, MaxRetriesExceeded

OUTPUT_FILE = _ROOT / "outputs" / "super_organised_content_for_cover_letter.md"

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a document structure organiser. Your ONLY task is to redistribute existing bullet points into 4 labelled sections for a cover letter.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. DO NOT write new content — not a single new word beyond what exists in the input
2. DO NOT improve, polish, or rephrase any bullet points — take them as-is
3. DO NOT add new bullet points not already present in the input
4. DO NOT remove bullet points — every point from the input must appear in exactly one output section
5. ONLY redistribute existing bullets into the best-fit section
6. PRESERVE the first-person voice of every bullet exactly — never convert "I built..." or "I led..." to "Candidate built..." or  "The candidate has..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE 4 TARGET SECTIONS AND THEIR CONTENT CRITERIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"einleitung" — Opening section (~50 words of material, max 3 key ideas)
  → Include bullets about: motivation for applying, why this specific company, how the role was found, genuine excitement for what the company does

"hauptteil" — Main body section (~150–200 words of material, 3 sub-paragraphs worth)
  → Include bullets about: skills matching job requirements, concrete experiences as proof of ability, 5-year growth narrative, specific technical contributions, JD coverage evidence, profile fit

"company_fit" — Company-fit paragraph (~2 lines of material)
  → Include bullets about: values alignment with company culture, working style matching company's team culture, specific cultural connection points

"schluss" — Closing section (~50 words of material)
  → Include bullets about: interview request, availability, active closing sentiment, preparation signals that belong at the end

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RETURN FORMAT (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return a valid JSON object with exactly these 4 keys.
The values must be arrays of strings (the redistributed bullet points).
No markdown fences. No preamble. No explanation. ONLY the JSON object.

{
  "einleitung": ["bullet point text as-is", "another bullet"],
  "hauptteil": ["bullet point text as-is", "another bullet", "and so on"],
  "company_fit": ["bullet point text as-is"],
  "schluss": ["bullet point text as-is"]
}"""


def _parse_json_response(raw_text: str) -> dict:
    """
    Safely parse the JSON response from the LLM.
    Handles edge cases like markdown fences being added despite instruction.
    """
    text = raw_text.strip()

    # Strip markdown fences if present (defensive)
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()

    try:
        data = json.loads(text)
        # Validate structure — ensure all 4 keys are present
        for key in ("einleitung", "hauptteil", "company_fit", "schluss"):
            if key not in data:
                data[key] = []
            elif not isinstance(data[key], list):
                data[key] = [str(data[key])]
        return data
    except json.JSONDecodeError:
        # Fallback: put everything in hauptteil so no content is lost
        return {
            "einleitung": [],
            "hauptteil": [raw_text],
            "company_fit": [],
            "schluss": [],
        }


def _sections_to_markdown(data: dict) -> str:
    """Convert the 4-section dict to a structured, human-readable Markdown document."""
    section_meta = {
        "einleitung": ("## Section 1: Opening (Einleitung)", "~50 words · 3 sentences max · motivation + why this company + how role found"),
        "hauptteil":  ("## Section 2: Main Body (Hauptteil)", "~150–200 words · 3 sub-paragraphs · skills + experience + concrete proof + growth"),
        "company_fit": ("## Section 3: Company-Fit Paragraph", "~2 lines · values/working style connected to company's specific culture & goals"),
        "schluss":    ("## Section 4: Closing (Schluss)", "~50 words · 1–2 sentences · active-voice interview request + availability"),
    }

    md_lines = ["# Organised Cover Letter Content\n"]
    md_lines.append("> Bullet points redistributed from Agent 4 output into the 4 cover letter sections.\n")
    md_lines.append("> Agent 6 will use this document to write the final cover letter.\n\n---\n")

    for key in ("einleitung", "hauptteil", "company_fit", "schluss"):
        heading, guidance = section_meta[key]
        md_lines.append(f"{heading}\n*{guidance}*\n")
        bullets = data.get(key, [])
        if bullets:
            for bullet in bullets:
                # Normalise: strip leading dashes/asterisks if already present
                clean = bullet.strip().lstrip("-").lstrip("*").strip()
                md_lines.append(f"- {clean}")
        else:
            md_lines.append("- *(No content mapped to this section)*")
        md_lines.append("\n")

    return "\n".join(md_lines)


def run(api_key: str, unorganised_points_md: str) -> str:
    """
    Execute Agent 5: organise bullet points into 4 cover letter sections.

    Args:
        api_key: Gemini API key.
        unorganised_points_md: Agent 4 output (raw bullet points across 7 dimensions).

    Returns:
        Markdown string with content mapped to 4 cover letter sections.
    """
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)

    user_message = (
        "---UNORGANISED CONTENT START---\n"
        f"{unorganised_points_md}\n"
        "---UNORGANISED CONTENT END---\n\n"
        "Redistribute ALL the bullet points above into the 4 cover letter sections.\n"
        "Return ONLY the valid JSON object. No other text, no explanation, no fences."
    )

    response = generate_with_retry(
        client,
        model="gemini-3-flash-preview",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",  # Force JSON output
            temperature=0.2,                         # Low temp for structured task
            max_output_tokens=8192,
        ),
    )

    raw_text = response.text
    data = _parse_json_response(raw_text)
    result = _sections_to_markdown(data)
    OUTPUT_FILE.write_text(result, encoding="utf-8")
    return result


# ── LangGraph Node Wrapper ────────────────────────────────────────────────────
def node(state: CoverLetterState) -> dict:
    try:
        result = run(state["api_key"], state["unorganised_points_md"])
        return {
            "organised_sections_md": result,
            "current_agent": "agent_5_complete",
        }
    except Exception as exc:             # ← catches everything including MaxRetriesExceeded
        raise RuntimeError(
            f"Agent X failed — pipeline stopped: {exc}"
        ) from exc
