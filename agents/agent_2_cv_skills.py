"""
Agent 2 — CV Skills Writer + Merger
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No web search. Pure generation task.

Task  : Generate a structured skills section aligned with the JD,
        then merge it into the candidate's existing CV (cv.md).
Input : job_description (from state); cv.md read from disk
Output: skills_added_cv.md
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

CV_FILE    = _ROOT / "cv.md"
OUTPUT_FILE = _ROOT / "outputs" / "skills_added_cv.md"

# ── System Prompt 1: Skills Section Generator ────────────────────────────────
SKILLS_SYSTEM_PROMPT = """You are an expert CV writer and career strategist, specialising in mentioned roles in the <Job Description> in the German and European job market.

YOUR TASK:
Generate a professional SKILLS SECTION for a CV, perfectly aligned with the provided Job Description.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE REQUIREMENTS (MANDATORY — no deviations)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Exactly 4 Major Skill Groups with clear, descriptive heading names derived from the JD
- Each Major Skill Group must have exactly 2 or 3 Sub-Skill Headers
- Each Sub-Skill Header must have at least 5 specific sub-skills (specific tools, frameworks, methods, domain-specific concepts, competencies — not generic terms like "programming" or "data analysis")
- Sub-skills are listed as comma-separated items — NO bullet points, NO sentences, NO explanations
- Priority order: first cover all skills explicitly mentioned in the JD, then add skills implied by the role's project context

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXACT OUTPUT FORMAT (copy this structure — replace placeholders)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---SKILLS START---

## Skills

**[Major Skill Group 1]**
*[Sub-Header 1 — ]:* Skill1, Skill2, Skill3, Skill4, Skill5
*[Sub-Header 2 — ]:* Skill1, Skill2, Skill3, Skill4, Skill5
*[Sub-Header 3 — ]:* Skill1, Skill2, Skill3, Skill4, Skill5

**[Major Skill Group 2]**
*[Sub-Header 1]:* Skill1, Skill2, Skill3, Skill4, Skill5
*[Sub-Header 2]:* Skill1, Skill2, Skill3, Skill4, Skill5

**[Major Skill Group 3]**
*[Sub-Header 1]:* Skill1, Skill2, Skill3, Skill4, Skill5
*[Sub-Header 2]:* Skill1, Skill2, Skill3, Skill4, Skill5
*[Sub-Header 3]:* Skill1, Skill2, Skill3, Skill4, Skill5

**[Major Skill Group 4]**
*[Sub-Header 1]:* Skill1, Skill2, Skill3, Skill4, Skill5
*[Sub-Header 2]:* Skill1, Skill2, Skill3, Skill4, Skill5

---SKILLS END---

IMPORTANT: Output ONLY the block above between ---SKILLS START--- and ---SKILLS END---. No explanations, no preamble, no extra text."""



def _extract_skills_block(raw: str) -> str:
    """Pull only the content between the skill delimiters."""
    start = raw.find("---SKILLS START---")
    end   = raw.find("---SKILLS END---")
    if start != -1 and end != -1:
        return raw[start + len("---SKILLS START---"):end].strip()
    return raw.strip()  # fallback: use the whole response


def _insert_skills_into_cv(cv_content: str, skills_block: str) -> str:
    """Insert skills section right before the first ## heading (e.g. Work Experience)."""
    lines = cv_content.splitlines()
    insert_pos = len(lines)  # default: append at end if no ## found

    for i, line in enumerate(lines):
        if line.startswith("## "):
            insert_pos = i
            break

    injected = ["", skills_block, ""]
    merged = lines[:insert_pos] + injected + lines[insert_pos:]
    return "\n".join(merged)



def run(api_key: str, job_description: str) -> str:
    """
    Execute Agent 2: generate structured skills section and merge with cv.md.

    Args:
        api_key: Gemini API key.
        job_description: Full JD text.

    Returns:
        Merged CV markdown string.
    """
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)

    # ── Step 1: Generate the skills section ──────────────────────────────
    skills_message = (
        "---JOB DESCRIPTION START---\n"
        f"{job_description}\n"
        "---JOB DESCRIPTION END---\n\n"
        "Generate the skills section following the exact structure and format requirements.\n"
        "Make sure every skill is specific and relevant to this JD. No generic placeholders."
    )

    skills_response = generate_with_retry(
        client,
        model="gemini-3-flash-preview",
        contents=skills_message,
        config=types.GenerateContentConfig(
            system_instruction=SKILLS_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=4096,
        ),
    )
    skills_section = skills_response.text

    # ── Step 2: Read the existing CV ─────────────────────────────────────
    if CV_FILE.exists():
        cv_content = CV_FILE.read_text(encoding="utf-8")
    else:
        cv_content = (
            "# [Candidate Name]\n\n"
            "⚠️ cv.md not found. Please place your CV (without skills/profile summary) "
            "as cv.md in the project root directory and re-run.\n\n"
            "## Work Experience\n[placeholder]\n\n"
            "## Education\n[placeholder]\n"
        )
    # ── Step 3: Merge skills into CV ───────────────────────────────────
    # Pure Python merge — no LLM call
    skills_block = _extract_skills_block(skills_section)
    result = _insert_skills_into_cv(cv_content, skills_block)
    OUTPUT_FILE.write_text(result, encoding="utf-8")
    return result


# ── LangGraph Node Wrapper ────────────────────────────────────────────────────
def node(state: CoverLetterState) -> dict:
    try:
        result = run(state["api_key"], state["job_description"])
        return {
            "skills_cv_md": result,
            "current_agent": "agent_2_complete",
        }
    except Exception as exc:             # ← catches everything including MaxRetriesExceeded
        raise RuntimeError(
            f"Agent X failed — pipeline stopped: {exc}"
        ) from exc