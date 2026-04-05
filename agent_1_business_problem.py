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

# ── Ensure project root is on sys.path so `state` can be imported ──────
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from google import genai
from google.genai import types
from state import CoverLetterState

OUTPUT_FILE = _ROOT / "outputs" / "The_Core_Business_Problem_and_how_it_was_solved.md"

# ── System Prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a corporate research analyst with deep expertise in technology and industry described in Job Description .

YOUR TASK:
Research the CORE BUSINESS PROBLEM this company is solving, specifically in the context of the attached Job Description. Find how they have actually approached or solved this problem — not what blogs say, but what the company itself has demonstrated.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY RESEARCH CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. DO NOT ASSUME anything — every fact must come from a verified primary source you actually searched.
2. Perform AT LEAST 3 web searches from different angles before generating your response.
3. Think step by step before writing your final output.
4. ONLY use these source types:
   - Official company website (About, Engineering, Blog, News pages)
   - Official company engineering or tech blog, newsroom, or insights page (on company domain or official Medium/LinkedIn account)
   - Official GitHub repositories, whitepapers, or case studies with explanations published by named company employees (if applicable to the role)
   - Official press releases, investor pages, or technical whitepapers
5. REJECT these sources entirely:
   - Third-party tech blogs (random Medium authors, dev.to, Towards Data Science, Analytics Vidhya)
   - News aggregators (TechCrunch, VentureBeat) — unless they directly quote company sources
   - Anonymous forums (Reddit, Stack Overflow, Hacker News)
   - Marketing content from competitors or vendors
   - Generic "top 10 companies using the mentioned technology" style articles

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEARCH STRATEGY (execute in this order)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Search 1: "[Company Name] engineering blog [main technical domain from JD]"
Search 2: "[Company Name] [specific technical challenge from JD] how we built it or our approach"
Search 3: "[Company Name] [key tool/framework from JD] production case study"
Search 4: site:[company official domain] [technical topic]
Search 5 (if needed): "[Company Name] technical architecture [relevant system]" 2024 OR 2025 OR 2026

⚠️ CAUTION: Companies often have large, multi-part problems. Focus ONLY on the part that the JD role would contribute to. Do not document the entire company's tech — only what's relevant to THIS role.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (strict Markdown — follow exactly)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Core Business Problem — [Company Name]
## Role Under Analysis: [Job Title from JD]

---

## 1. The Business Problem
[Clear, specific description of the business-level problem. What outcome is the company trying to achieve? Why does it matter to their business?]

## 2. The Technical Challenge
[The specific engineering or operational, functional, or domain challenge that this role must address. Be precise — what problem is the company trying to solve in this area?]

## 3. How the Company Actually Solves It
[Describe their real approach — strategic strategic architecture decisions, tools or processes, methodology. Be specific. Cite sources inline.]

### Verified Findings:
- **Finding 1**: [Description of what they actually did/built] — *Source: [URL]*
- **Finding 2**: [Description] — *Source: [URL]*
- **Finding 3**: [Description] — *Source: [URL]*

## 4. Role Contribution Mapping
[If this exact JD role existed here, what would this person own or directly contribute to the solution? Be specific about responsibilities.]

## 5. Skills in Context
| JD Skill | How This Company Uses It | Evidence / Source |
|----------|--------------------------|-------------------|
| [Skill]  | [Specific usage]         | [URL or document] |

## 6. Sources Consulted
- [URL]: [Brief description of what this source contained]
- [URL]: [Brief description]
"""


def run(api_key: str, job_description: str) -> str:
    """
    Execute Agent 1: research the core business problem with mandatory web search.

    Args:
        api_key: Gemini API key from the user.
        job_description: Full text of the job description.

    Returns:
        Markdown string with the research findings.
    """
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    client = genai.Client(api_key=api_key)

    user_message = (
        "---JOB DESCRIPTION START---\n"
        f"{job_description}\n"
        "---JOB DESCRIPTION END---\n\n"
        "Now execute your research following all mandatory constraints and the search strategy.\n"
        "Do NOT generate your response until you have performed at least 3 web searches from different angles.\n"
        "Think step by step: first identify the company and role, then search, then synthesise."
    )

    response = client.models.generate_content(
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
    OUTPUT_FILE.write_text(result, encoding="utf-8")
    return result


# ── LangGraph Node Wrapper ────────────────────────────────────────────────────
def node(state: CoverLetterState) -> dict:
    """LangGraph node — wraps run() and returns state update dict."""
    try:
        result = run(state["api_key"], state["job_description"])
        return {
            "business_problem_md": result,
            "current_agent": "agent_1_complete",
        }
    except Exception as exc:
        error_msg = f"Agent 1 (Business Problem Research) failed: {exc}"
        return {
            "business_problem_md": f"[AGENT 1 ERROR]\n\n{error_msg}",
            "errors": [error_msg],
            "current_agent": "agent_1_error",
        }
