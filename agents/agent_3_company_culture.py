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
from prompts.agent_3 import CULTURE_SYSTEM_PROMPT

OUTPUT_FILE = _ROOT / "outputs" / "company_vision_and_culture.md"






def run(api_key: str, company_name: str, output_dir: Path) -> str:

    """
    Execute Agent 3: research company vision and culture with mandatory web search.

    Args:
        api_key: Gemini API key.
        company_name: The name of the company to research.
        output_dir: The directory where the output file will be saved.

    Returns:
        Markdown string with vision & culture findings.
    """
    out_file = output_dir / "company_vision_and_culture.md"  # agent-specific name

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
    out_file.write_text(result, encoding="utf-8")    
    return result


# ── LangGraph Node Wrapper ────────────────────────────────────────────────────
def node(state: CoverLetterState) -> dict:
    try:
        output_dir = Path(state["run_output_dir"])
        result = run(state["api_key"], state["company_name"], output_dir)
        return {
            "culture_md": result,
            "current_agent": "agent_3_complete",
        }
    except Exception as exc:             # ← catches everything including MaxRetriesExceeded
        raise RuntimeError(
            f"Agent 3 failed — pipeline stopped: {exc}"
        ) from exc