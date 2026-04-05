"""
Agent 3 — Company Vision & Culture Research
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mandatory web search (GoogleSearch grounding via Gemini API).

Task  : Research the company's overall vision, culture, and values.
        Extracts the company name from Agent 1's output first.
Input : business_problem_md (from state, Agent 1's output)
Output: company_vision_and_culture.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from google import genai
from google.genai import types
from state import CoverLetterState

OUTPUT_FILE = _ROOT / "outputs" / "company_vision_and_culture.md"

# ── System Prompt: Company Name Extractor ─────────────────────────────────────
EXTRACT_NAME_PROMPT = """You are a data extractor.
From the provided document, extract ONLY the company name.
Return ONLY the company name as plain text — no other words, no punctuation beyond what is part of the name itself, no explanation."""

# ── System Prompt: Culture Researcher ────────────────────────────────────────
CULTURE_SYSTEM_PROMPT = """You are a cultural intelligence researcher specialising in organisational culture, leadership philosophy, and employer branding.

YOUR TASK:
Research and document the VISION, CULTURE, and VALUES of the specified company, as publicly stated by the company itself.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY RESEARCH CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. DO NOT ASSUME anything — every claim must come from a primary, verified company source.
2. Perform AT LEAST 3 web searches from different angles before generating your response.
3. Think step by step before writing your final output.
4. PREFERRED SOURCES (ranked by priority):
   ✅ Official "About Us" / "Mission" / "Values" / "Culture" pages on company website
   ✅ CEO or founder talks on the OFFICIAL company YouTube channel
   ✅ Official company blog posts about culture, team, or leadership
   ✅ Official careers/jobs pages that describe the work environment
   ✅ LinkedIn official company page (only official posts, not individual opinions)
   ✅ Official press interviews where founders or executives speak about culture
5. AVOID:
   ❌ Glassdoor or Indeed employee reviews
   ❌ Anonymous forum posts or social media comments
   ❌ Third-party HR or culture analysis articles
   ❌ Recruitment agency blogs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEARCH STRATEGY (execute in this order)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Search 1: "[Company Name] company mission vision values official"
Search 2: "[Company Name] CEO founder culture leadership philosophy"
Search 3: "[Company Name] work culture how we work team values"                           
Search 4: "[Company Name] company about us careers culture"
Search 5 (if needed): "[Company Name] CEO YouTube interview company values"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (strict Markdown — follow exactly)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# [Company Name] — Vision & Culture

---

## 1. Core Mission & Vision
[Official mission statement and long-term vision — what the company ultimately exists to do]
*Source: [URL]*

## 2. Stated Values & Principles
[The company's official values, principles, or cultural pillars — list them with brief explanations if provided officially]
*Source: [URL]*

## 3. Leadership Philosophy
[What the founders or executives say about how they lead, build teams, and make decisions — their publicly stated management approach]
*Source: [URL]*

## 4. Innovation & Operational Culture
[How they approach their core work: experimentation, standards of excellence, learning from failure, and their stance on change and continuous improvement]
*Source: [URL]*


## 5. Team & Work Environment
[What working there actually looks like — collaboration style, autonomy level, growth opportunities, work-life approach]
*Source: [URL]*

## 6. Key Cultural Signals for a Cover Letter
[5–7 specific, non-obvious facts about this company's culture that a cover letter candidate should reference to prove genuine cultural research — not generic, not things that apply to most companies in this industry]
- Signal 1: [specific insight + why it matters]
- Signal 2: [specific insight + why it matters]
- Signal 3: ...

## 7. Sources Consulted
- [URL]: [Brief description of what this source confirmed]
- [URL]: [Brief description]
"""


def _extract_company_name(client: genai.Client, business_problem_md: str) -> str:
    """
    Use a small, fast LLM call to extract the company name from Agent 1's output.
    Falls back to 'the company' if extraction fails.
    """
    try:
        # Use the first 3000 chars — the company name appears near the top
        snippet = business_problem_md[:3000]
        response = client.models.generate_content(
            model="gemini-3-flash",
            contents=f"Extract the company name from this document:\n\n{snippet}",
            config=types.GenerateContentConfig(
                system_instruction=EXTRACT_NAME_PROMPT,
                temperature=0.1,
                max_output_tokens=50,
            ),
        )
        name = response.text.strip()
        # Sanity check — if it's too long it's probably not a company name
        return name if len(name) < 100 else "the company"
    except Exception:
        return "the company"


def run(api_key: str, business_problem_md: str) -> str:
    """
    Execute Agent 3: research company vision and culture with mandatory web search.

    Args:
        api_key: Gemini API key.
        business_problem_md: Agent 1's output (used to extract company name).

    Returns:
        Markdown string with vision & culture findings.
    """
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)

    company_name = _extract_company_name(client, business_problem_md)

    user_message = (
        f"Research the vision, culture, and values of: **{company_name}**\n\n"
        "Follow ALL mandatory research constraints — perform at least 3 web searches from different "
        "angles before generating your response.\n"
        f"The company name to research is: {company_name}\n\n"
        "Think step by step:\n"
        "1. Identify the company's official web presence\n"
        "2. Search for official mission/values pages\n"
        "3. Search for leadership talks and culture documentation\n"
        "4. Synthesise only what you found from verified primary sources\n"
        "5. Write your output in the required format"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=CULTURE_SYSTEM_PROMPT,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=1.0,
            max_output_tokens=8192,
        ),
    )

    result = response.text
    OUTPUT_FILE.write_text(result, encoding="utf-8")
    return result


# ── LangGraph Node Wrapper ────────────────────────────────────────────────────
def node(state: CoverLetterState) -> dict:
    try:
        result = run(state["api_key"], state["business_problem_md"])
        return {
            "culture_md": result,
            "current_agent": "agent_3_complete",
        }
    except Exception as exc:
        error_msg = f"Agent 3 (Company Culture Research) failed: {exc}"
        return {
            "culture_md": f"[AGENT 3 ERROR]\n\n{error_msg}",
            "errors": [error_msg],
            "current_agent": "agent_3_error",
        }
