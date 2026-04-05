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

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from google import genai
from google.genai import types
from state import CoverLetterState

OUTPUT_FILE = _ROOT / "outputs" / "final_cover_letter.md"

# ── System Prompt: Writer ─────────────────────────────────────────────────────
WRITER_SYSTEM_PROMPT = """You are a professional cover letter writer specialising in the German job market, writing in English for professional role the candidate is applying for the Job in Germany.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY WRITING RULES — ALL MUST BE FOLLOWED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. FIRST PERSON "I" THROUGHOUT — Most sentence uses "I" as the subject or includes "I" clearly somewhere in the sentence. No passive constructions that hide the person.
2. SHORT, CLEAR SENTENCES — maximum one clause per sentence. Break compound sentences into two.
3. NO BRAGGING — forbidden: "I am the best", "highly skilled", "exceptional talent", "outstanding", "perfect candidate"
4. NO COMPANY CRITICISM — if they lack something, write: "I want to help build X" not "you don't have X yet"
5. GENUINE, WARM TONE — enthusiasm must feel real and earned through specific details, not performed through adjectives
6. ACTIVE VOICE IN CLOSING — forbidden: Konjunktiv ("would like to"), passive constructions. Write: "I look forward to meeting you" not "I would love to potentially maybe have the chance to..."
7. DO NOT BRAG ABOUT BEING A FAST LEARNER — show it through what you built or achieved instead

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTELY FORBIDDEN PHRASES (do not let any of these appear)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ "I am passionate about"
❌ "I am a fast learner"
❌ "synergy" / "leverage" / "utilize" / "utilise"
❌ "I believe I am the perfect candidate"
❌ "team player"
❌ "results-driven"
❌ "detail-oriented"
❌ "I would love to" / "I would like to"
❌ "dynamic" / "innovative" (as self-description — "I am a dynamic innovator")
❌ "I am excited to" (replace with specific reason for interest)
❌ Any phrase a CV generator would produce

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COVER LETTER STRUCTURE — 5 PARAGRAPHS (DIN 5008 style, in English)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PARAGRAPH 1 — OPENING (Einleitung) ~50 words, max 3 sentences:
  → Sentence 1: State your motivation for THIS role specifically
  → Sentence 2: Say why THIS specific company (show you researched them — be specific)
  → Sentence 3: Mention how you found the role (optional but humanising)

PARAGRAPH 2 — MAIN BODY PART 1 ~50–70 words:
  → One or two specific skills or experiences linked to job requirements
  → Use a concrete project or achievement as proof — not just claims
  → Make the connection to the role explicit

PARAGRAPH 3 — MAIN BODY PART 2 ~50–70 words:
  → A different skill or experience dimension from Paragraph 2
  → Different proof than used in Paragraph 2
  → Can include the 5-year growth dimension if it fits naturally

PARAGRAPH 4 — COMPANY FIT ~2 sentences, ~40 words:
  → Connect your values or way of working to the company's specific culture
  → Reference something specific about the company's culture (shows research)

PARAGRAPH 5 — CLOSING (Schluss) ~50 words, 1–2 sentences:
  → Request an interview directly and actively (no Konjunktiv)
  → State your availability
  → End warmly but professionally

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Return ONLY the cover letter text — no meta-commentary, no "Here is your cover letter:"
- Write in first-person voice throughout — the reader must always feel 
  the candidate is speaking directly. "I" must appear in every paragraph 
  naturally, but do NOT start consecutive sentences with "I". 
  Vary structure: lead with context ("At [employer], I..."), 
  outcomes ("The system I built..."), or company references 
  ("Your approach to X aligns with what I worked on at...").
- Start with the greeting: "Dear [Hiring Manager / Hiring Team],"
- End with professional sign-off: "Best regards," followed by "[Your Name]"
- Do not include a date, address block, or reference number (those are added separately)"""

# ── System Prompt: Self-Critique Auditor ─────────────────────────────────────
CRITIQUE_SYSTEM_PROMPT = """You are a cover letter quality auditor for the German job market.

Review the cover letter below against exactly these constraints. Be strict — flag even subtle violations.

CONSTRAINTS TO CHECK:
1. First-person "I" used throughout (not passive or third-person constructions)?
2. Sentences are short and clear — no compound-complex sentences with multiple clauses?
3. None of these forbidden phrases appear: "passionate about", "fast learner", "synergy", "leverage", "utilize", "utilise", "perfect candidate", "team player", "results-driven", "detail-oriented", "I would love to", "I would like to", "dynamic" (as self-description), "innovative" (as self-description), "I am excited to"?
4. No bragging, no superlatives, no "I am the best/exceptional/outstanding"?
5. Company is never criticised — no "you lack X", "you don't have Y"?
6. Closing is in active voice — no Konjunktiv constructions?
7. 5-paragraph structure followed approximately (Opening, Main Body ×2, Company Fit, Closing)?
8. Genuine tone — enthusiasm backed by specific details, not hollow adjectives?

Return a JSON object with exactly this structure. No other text:
{
  "has_violations": true,
  "violations": ["specific violation 1 with the exact phrase", "specific violation 2"],
  "approved": false
}

Or if no violations:
{
  "has_violations": false,
  "violations": [],
  "approved": true
}"""


def _write_letter(client: genai.Client, organised_sections_md: str) -> str:
    """First pass: generate the cover letter from organised sections."""
    response = client.models.generate_content(
        model="gemini-3-flash",
        contents=(
            "---ORGANISED COVER LETTER SECTIONS START---\n"
            f"{organised_sections_md}\n"
            "---ORGANISED COVER LETTER SECTIONS END---\n\n"
            "Write the cover letter now based on the content in these sections.\n"
            "Follow all writing rules and the 4-paragraph structure strictly.\n"
            "Use only the content provided — do not invent facts not present in the sections."
        ),
        config=types.GenerateContentConfig(
            system_instruction=WRITER_SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=2048,
        ),
    )
    return response.text


def _critique_letter(client: genai.Client, letter: str) -> dict:
    """Second pass: audit the draft for constraint violations."""
    response = client.models.generate_content(
        model="gemini-3-flash",
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
    try:
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1]).strip()
        return json.loads(raw)
    except (json.JSONDecodeError, Exception):
        # If critique itself fails, assume no violations and proceed
        return {"has_violations": False, "violations": [], "approved": True}


def _regenerate_with_feedback(
    client: genai.Client,
    organised_sections_md: str,
    draft: str,
    violations: list[str],
) -> str:
    """Third pass: regenerate fixing the specific violations identified."""
    violations_text = "\n".join(f"  - {v}" for v in violations)

    response = client.models.generate_content(
        model="gemini-3-flash",
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
            max_output_tokens=2048,
        ),
    )
    return response.text


def run(api_key: str, organised_sections_md: str) -> str:
    """
    Execute Agent 6: write the final cover letter with self-critique loop.

    Args:
        api_key: Gemini API key.
        organised_sections_md: Agent 5 output (4 sections of organised bullet points).

    Returns:
        The final polished cover letter as a string.
    """
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)

    # Pass 1 — Initial draft
    letter = _write_letter(client, organised_sections_md)

    # Pass 2 — Self-critique
    critique = _critique_letter(client, letter)

    # Pass 3 — Regenerate if violations found (conditional LangGraph edge pattern)
    if critique.get("has_violations") and critique.get("violations"):
        letter = _regenerate_with_feedback(
            client,
            organised_sections_md,
            letter,
            critique["violations"],
        )

    OUTPUT_FILE.write_text(letter, encoding="utf-8")
    return letter


# ── LangGraph Node Wrapper ────────────────────────────────────────────────────
def node(state: CoverLetterState) -> dict:
    try:
        result = run(state["api_key"], state["organised_sections_md"])
        return {
            "final_cover_letter_md": result,
            "current_agent": "agent_6_complete",
        }
    except Exception as exc:
        error_msg = f"Agent 6 (Cover Letter Writer) failed: {exc}"
        return {
            "final_cover_letter_md": f"[AGENT 6 ERROR]\n\n{error_msg}",
            "errors": [error_msg],
            "current_agent": "agent_6_error",
        }
