# AI Cover Letter Generator — 6-Agent Pipeline

A production-grade multi-agent cover letter generation system built with:
- **LangGraph 0.3.x** — Sequential StateGraph orchestration
- **Gemini 2.5 Pro** (`google-genai` ≥ 1.10.0 unified SDK) — LLM backbone
- **Google Search Grounding** — Native Gemini web search (no Tavily needed)
- **Gradio 5.x** — Streaming web UI

---

## Architecture

```
START → Agent 1 → Agent 2 → Agent 3 → Agent 4 → Agent 5 → Agent 6 → END
         │Web      │NoWeb    │Web      │NoWeb    │NoWeb    │NoWeb
         ▼         ▼         ▼         ▼         ▼         ▼
     Business   CV Skills  Culture  CL Points  Organise  Write
     Problem    Merger     Research  (7 dims)  (4 para)  Letter
```

| Agent | Input | Output File |
|-------|-------|-------------|
| 1 | Job Description | `The_Core_Business_Problem_and_how_it_was_solved.md` |
| 2 | JD + cv.md | `skills_added_cv.md` |
| 3 | Agent 1 output (for company name) | `company_vision_and_culture.md` |
| 4 | Agents 1 + 2 + 3 outputs | `unorganised_cover_letter_content.md` |
| 5 | Agent 4 output | `super_organised_content_for_cover_letter.md` |
| 6 | Agent 5 output | `final_cover_letter.md` |

---

## Setup

### 1. Prerequisites

- Python 3.11 or 3.12
- A **Gemini API key** with access to `gemini-2.5-pro`  
  Get one at: https://aistudio.google.com/apikey

### 2. Install dependencies

```bash
# From the project root (cover_letter_agent/)
pip install -r requirements.txt
```

### 3. Prepare your CV

Edit `cv.md` in the project root with your actual CV content.

**Important:**
- ❌ Do NOT include a Skills section (Agent 2 generates this from the JD)
- ❌ Do NOT include a Profile Summary (Agent 6 derives this)
- ✅ DO include: Work Experience, Education, Projects, Certifications, Languages, Hobbies

### 4. Run the UI

```bash
python ui.py
```

Open your browser at: **http://localhost:7860**

---

## Usage

1. Paste your **Gemini API key** into the password field
2. Paste the **full job description** into the text area
3. Click **"Generate Cover Letter"**
4. Wait — the pipeline takes **15–25 minutes** total:
   - Agents 1 and 3 do live deep web research (3–5 min each)
   - Agents 2, 4, 5, 6 are pure generation (1–2 min each)
5. Watch each tab populate as agents complete
6. Download the final cover letter when Agent 6 finishes

---

## Project Structure

```
cover_letter_agent/
├── cv.md                          ← Your CV (no skills/summary) — edit this!
├── requirements.txt
├── state.py                       ← LangGraph TypedDict state schema
├── graph.py                       ← StateGraph definition + compile
├── ui.py                          ← Gradio 5.x interface
├── agents/
│   ├── __init__.py
│   ├── agent_1_business_problem.py   ← Web search
│   ├── agent_2_cv_skills.py          ← CV skills generator + merger
│   ├── agent_3_company_culture.py    ← Web search
│   ├── agent_4_cover_points.py       ← CRISPE-structured synthesis
│   ├── agent_5_organise.py           ← JSON output, 4-section organiser
│   └── agent_6_write_letter.py       ← Writer + self-critique loop
├── inputs/
│   └── (job descriptions saved here at runtime)
└── outputs/
    ├── The_Core_Business_Problem_and_how_it_was_solved.md
    ├── skills_added_cv.md
    ├── company_vision_and_culture.md
    ├── unorganised_cover_letter_content.md
    ├── super_organised_content_for_cover_letter.md
    └── final_cover_letter.md
```

---

## Key Design Decisions

### Why `google-genai` (not `google-generativeai`)?
The new unified `google-genai` SDK (≥ 1.0.0) is the current standard as of 2025/2026. The old `google-generativeai` package is deprecated.

### Why native GoogleSearch grounding?
Gemini 2.5 Pro supports native Google Search grounding via `types.Tool(google_search=types.GoogleSearch())`. This is more reliable than external search APIs and doesn't require a Tavily or SerpAPI key.

### Why `stream_mode="values"` in LangGraph?
Streaming with `"values"` mode yields the full state snapshot after each node completes. This lets the Gradio UI update one tab at a time as agents finish, rather than waiting for the entire pipeline.

### Why a self-critique loop in Agent 6?
Agent 6 runs a second LLM call auditing the draft cover letter against the writing constraints (forbidden phrases, sentence length, active voice). If violations are found, it regenerates with the violations as feedback. This pattern is similar to LangGraph's conditional edge pattern.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'google.genai'` | Run `pip install google-genai>=1.10.0` |
| `ModuleNotFoundError: No module named 'langgraph'` | Run `pip install langgraph>=0.3.0` |
| API key error | Verify key at https://aistudio.google.com — check if Gemini 2.5 Pro is enabled |
| Agent 1 or 3 returns no sources | Web search grounding is working but found no official sources — the prompt instructs the model not to use unofficial sources |
| `cv.md not found` warning in Agent 2 output | Place your CV file at the project root as `cv.md` |
| Pipeline hangs | Web search agents (1, 3) can take 3–5 min each — be patient. If it exceeds 15 min, check your API quota |

---

## Notes on Prompt Engineering

Each agent uses a specific prompt engineering approach:

- **Agent 1 & 3**: Role + Constraints + Ordered Search Strategy + Strict Output Format + Chain-of-Thought trigger
- **Agent 2**: Two-stage prompting (generate then merge) with strict format specification
- **Agent 4**: Full CRISPE framework (Context, Role, Instructions, Steps, Persona, Examples)
- **Agent 5**: Highly constrained redistribution task with `response_mime_type="application/json"` to enforce structure
- **Agent 6**: Negative constraints (forbidden phrases list) + structural contract + self-critique loop
