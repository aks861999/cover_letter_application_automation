"""
ui.py — Gradio 5.x interface for the Cover Letter Generation Pipeline.

User inputs:
  • Gemini API key (password field)
  • Job description (large text area)

Output tabs (one per agent, updated via streaming as each completes):
  • Tab 1: Business Problem Research
  • Tab 2: Enhanced CV with Skills
  • Tab 3: Company Vision & Culture
  • Tab 4: Cover Letter Points
  • Tab 5: Organised Sections
  • Tab 6: Final Cover Letter

Download button becomes visible when Agent 6 finishes.
"""
from pathlib import Path
import gradio as gr
from graph import graph
from state import CoverLetterState

# ── Constants ─────────────────────────────────────────────────────────────────
AGENT_LABELS = [
    "🔍 Agent 1: Business Problem",
    "📝 Agent 2: CV + Skills",
    "🏢 Agent 3: Company Culture",
    "💡 Agent 4: Cover Letter Points",
    "📋 Agent 5: Organised Sections",
    "✉️  Agent 6: Final Cover Letter",
]

# Keys in state that each agent populates (in pipeline order)
AGENT_STATE_KEYS = [
    "business_problem_md",
    "skills_cv_md",
    "culture_md",
    "unorganised_points_md",
    "organised_sections_md",
    "final_cover_letter_md",
]

FINAL_OUTPUT_PATH = Path("outputs/final_cover_letter.md")


# ── Pipeline Generator ────────────────────────────────────────────────────────
def run_pipeline(api_key: str, job_description: str):
    """
    Generator function that runs the full 6-agent LangGraph pipeline
    and yields UI updates after each agent completes.

    Yields tuples of:
        (status_text, out1, out2, out3, out4, out5, out6, download_update)
    matching the 8 Gradio output components defined in build_ui().
    """
    # ── Input validation ──────────────────────────────────────────────────
    if not api_key or not api_key.strip():
        yield (
            "⚠️ Please enter your Gemini API key in the field above.",
            "", "", "", "", "", "",
            gr.update(visible=False),
        )
        return

    if not job_description or not job_description.strip():
        yield (
            "⚠️ Please paste the Job Description before clicking Generate.",
            "", "", "", "", "", "",
            gr.update(visible=False),
        )
        return

    # ── Build initial state ───────────────────────────────────────────────
    initial_state: CoverLetterState = {
        "api_key":               api_key.strip(),
        "job_description":       job_description.strip(),
        "business_problem_md":   "",
        "skills_cv_md":          "",
        "culture_md":            "",
        "unorganised_points_md": "",
        "organised_sections_md": "",
        "final_cover_letter_md": "",
        "errors":                [],
        "current_agent":         "starting",
    }

    # ── Yield initial status before pipeline starts ───────────────────────
    outputs = [""] * 6
    status = (
        "🚀 Pipeline started — running Agent 1 (deep web research).\n"
        "⏳ Agents 1 and 3 use live web search — each may take 3–5 minutes. Please wait."
    )
    yield (status, *outputs, gr.update(visible=False))

    # ── Track which agent outputs have been captured ──────────────────────
    captured = [False] * 6

    try:
        # LangGraph stream: yields the FULL state after each node completes
        for state_snapshot in graph.stream(initial_state, stream_mode="values"):
            updated = False

            for i, key in enumerate(AGENT_STATE_KEYS):
                value = state_snapshot.get(key, "")
                # Only update the UI when this field transitions from empty → filled
                if value and not captured[i]:
                    outputs[i] = value
                    captured[i] = True
                    updated = True

                    # Build status message
                    next_idx = i + 1
                    if next_idx < 6:
                        next_label = AGENT_LABELS[next_idx]
                        status = (
                            f"✅ {AGENT_LABELS[i]} — Complete\n"
                            f"🔄 Now running: {next_label}…"
                        )
                        if next_idx in (2,):  # Agent 3 also uses web search
                            status += "\n⏳ Web search agent — may take 3–5 minutes."
                    else:
                        status = "✅ All 6 agents complete! Your cover letter is ready below."

                    download_update = (
                        gr.update(value=str(FINAL_OUTPUT_PATH), visible=True)
                        if i == 5 and FINAL_OUTPUT_PATH.exists()
                        else gr.update(visible=False)
                    )
                    yield (status, *outputs, download_update)
                    break  # Yield once per agent completion event

            # Catch the very last state snapshot (all 6 complete)
            if all(captured) and not updated:
                break

        # ── Handle any accumulated errors ─────────────────────────────────
        errors = state_snapshot.get("errors", [])  # type: ignore[possibly-undefined]
        if errors:
            error_lines = "\n".join(f"  • {e}" for e in errors)
            status = f"✅ Pipeline complete (with errors):\n{error_lines}"

        # ── Final yield with download button ──────────────────────────────
        download_update = (
            gr.update(value=str(FINAL_OUTPUT_PATH), visible=True)
            if FINAL_OUTPUT_PATH.exists()
            else gr.update(visible=False)
        )
        yield (status, *outputs, download_update)

    except Exception as exc:
        status = (
            f"❌ Pipeline error: {exc}\n\n"
            "Possible causes:\n"
            "  • Invalid or expired Gemini API key\n"
            "  • Gemini API quota exceeded\n"
            "  • Network connectivity issue\n"
            "Check the terminal for the full traceback."
        )
        yield (status, *outputs, gr.update(visible=False))
        raise  # Re-raise so the terminal shows the full traceback


# ── UI Builder ────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
    .header-box { text-align: center; padding: 1rem 0; }
    .warning-box { background: #fff3cd; border-left: 4px solid #ffc107;
                   padding: 0.75rem 1rem; border-radius: 4px; margin: 0.5rem 0; }
    .status-complete { color: #198754; font-weight: bold; }
"""

THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.blue,
    secondary_hue=gr.themes.colors.indigo,
)


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="AI Cover Letter Generator — 6-Agent Pipeline") as demo:

        # ── Header ────────────────────────────────────────────────────────
        gr.Markdown(
            """
# 🤖 AI Cover Letter Generator
### 6-Agent Pipeline · Gemini 2.5 Pro + LangGraph + Google Search Grounding

**What each agent does:**
| Agent | Task | Web Search? |
|-------|------|-------------|
| 1 | Research core business problem + how company solved it | ✅ Mandatory |
| 2 | Generate JD-aligned skills section + merge into your CV | ❌ |
| 3 | Research company vision, culture & values | ✅ Mandatory |
| 4 | Generate raw cover letter ideas across 7 dimensions | ❌ |
| 5 | Organise ideas into 4 cover letter paragraphs | ❌ |
| 6 | Write final cover letter (with self-critique loop) | ❌ |

> 📄 **Before running:** Place your `cv.md` file (without skills/profile summary sections) in the project root directory.
            """,
            elem_classes=["header-box"],
        )

        # ── Input Row ─────────────────────────────────────────────────────
        with gr.Row(equal_height=False):
            with gr.Column(scale=1):
                api_key_input = gr.Textbox(
                    label="🔑 Gemini API Key",
                    placeholder="Paste your Gemini API key here (AIza...)",
                    type="password",
                    lines=1,
                    info="Get a key at https://aistudio.google.com/apikey — requires Gemini 2.5 Pro access.",
                )

                jd_input = gr.Textbox(
                    label="📋 Job Description",
                    placeholder=(
                        "Paste the full job description here.\n\n"
                        "Include everything: role title, responsibilities, requirements, "
                        "company info, and any application instructions."
                    ),
                    lines=22,
                    info="The more complete the JD, the better the research and cover letter.",
                )

                run_btn = gr.Button(
                    "🚀 Generate Cover Letter",
                    variant="primary",
                    size="lg",
                )

                gr.Markdown(
                    """
<div class="warning-box">
⚠️ <strong>Expected runtime: 15–25 minutes total</strong><br>
Agents 1 and 3 perform live deep web research using Gemini's native Google Search grounding.
Each search agent may take 3–5 minutes. Do not close this page during processing.
</div>
                    """
                )

        # ── Status Bar ────────────────────────────────────────────────────
        status_box = gr.Textbox(
            label="📊 Pipeline Status",
            value="Ready. Enter your API key and Job Description, then click Generate.",
            interactive=False,
            lines=3,
        )

        # ── Agent Output Tabs ─────────────────────────────────────────────
        tab_outputs: list[gr.Markdown] = []
        with gr.Tabs():
            for label in AGENT_LABELS:
                with gr.Tab(label=label):
                    output = gr.Markdown(
                        value=f"*Waiting for {label} to run…*",
                        height=500,
                    )
                    tab_outputs.append(output)

        # ── Download Button ───────────────────────────────────────────────
        download_file = gr.File(
            label="⬇️ Download Final Cover Letter (.md)",
            visible=False,
            file_count="single",
        )

        gr.Markdown(
            """
---
**Output files saved to `outputs/` directory:**
- `The_Core_Business_Problem_and_how_it_was_solved.md` — Agent 1
- `skills_added_cv.md` — Agent 2
- `company_vision_and_culture.md` — Agent 3
- `unorganised_cover_letter_content.md` — Agent 4
- `super_organised_content_for_cover_letter.md` — Agent 5
- `final_cover_letter.md` — Agent 6
            """
        )

        # ── Wire Run Button to Generator ──────────────────────────────────
        run_btn.click(
            fn=run_pipeline,
            inputs=[api_key_input, jd_input],
            outputs=[status_box, *tab_outputs, download_file],
            show_progress="hidden",  # We use our own status box
        )

    return demo


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ui = build_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        quiet=False,
        theme=THEME,
        css=CUSTOM_CSS,
    )
