"""
Agent 3 — Company Vision & Culture Research
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mandatory web search (GoogleSearch grounding via Gemini API).

Task  : Research the company's overall vision, culture, and values.
        Company name is provided directly by the user via UI.
Input : company_name (from state, entered by user)
Output: company_vision_and_culture.md
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

OUTPUT_FILE = _ROOT / "outputs" / "company_vision_and_culture.md"

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




def run(api_key: str, company_name: str) -> str:
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

    response = generate_with_retry(
        client,
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
        result = run(state["api_key"], state["company_name"])
        return {
            "culture_md": result,
            "current_agent": "agent_3_complete",
        }
    except Exception as exc:             # ← catches everything including MaxRetriesExceeded
        raise RuntimeError(
            f"Agent X failed — pipeline stopped: {exc}"
        ) from exc