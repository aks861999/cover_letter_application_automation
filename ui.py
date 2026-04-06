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
from utils import MaxRetriesExceeded

from pathlib import Path
import gradio as gr
from graph import graph
from state import CoverLetterState
from utils import make_run_dir

_ROOT = Path(__file__).parent

from agents.agent_1_business_problem import run as run_agent_1
from agents.agent_2_cv_skills        import run as run_agent_2
from agents.agent_3_company_culture  import run as run_agent_3
from agents.agent_4_cover_points     import run as run_agent_4
from agents.agent_5_organise         import run as run_agent_5
from agents.agent_6_write_letter     import run as run_agent_6




# ── In-memory session state ───────────────────────────────────────────────────
_session = {
    "api_key": "",
    "job_description": "",
    "company_name": "",
    "run_output_dir": None,
    "agent_1_output": None,
    "agent_2_output": None,
    "agent_3_output": None,
    "agent_4_output": None,
    "agent_5_output": None,
    "agent_6_output": None,
}


# ── Constants ─────────────────────────────────────────────────────────────────
AGENT_LABELS = [
    "🔍 Agent 1: Business Problem",
    "📝 Agent 2: CV + Skills",
    "🏢 Agent 3: Company Culture",
    "💡 Agent 4: Cover Letter Points",
    "📋 Agent 5: Organised Sections",
    "✉️  Agent 6: Final Cover Letter",
]

# Keys in LangGraph state that each agent populates (in pipeline order)
AGENT_STATE_KEYS = [
    "business_problem_md",
    "skills_cv_md",
    "culture_md",
    "unorganised_points_md",
    "organised_sections_md",
    "final_cover_letter_md",
]


import logging
from datetime import datetime

def _setup_run_logging(run_dir: Path) -> None:
    """
    Attach a FileHandler to the root logger pointing at the current run folder.
    Removes any previous FileHandler first to avoid duplicate log entries
    if multiple runs happen in the same session.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)

    # Remove any existing FileHandlers from previous runs
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root_logger.removeHandler(handler)

    # Create timestamped log file inside this run's output folder
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    log_file = run_dir / f"pipeline_debug_{timestamp}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root_logger.addHandler(file_handler)

# Matching keys in _session dict — must stay in sync with AGENT_STATE_KEYS order
_SESSION_KEYS = [
    "agent_1_output",
    "agent_2_output",
    "agent_3_output",
    "agent_4_output",
    "agent_5_output",
    "agent_6_output",
]


# ── Individual Agent Runners ──────────────────────────────────────────────────

def run_single_agent_1(api_key, job_description):
    run_dir = _session.get("run_output_dir")
    if not run_dir:
        run_dir = str(make_run_dir(_ROOT / "outputs", "manual_run"))
        _session["run_output_dir"] = run_dir
        _setup_run_logging(Path(run_dir))
    try:
        result = run_agent_1(api_key, job_description, Path(run_dir))
        _session["agent_1_output"] = result
        return result, f"✅ Agent 1 complete — saved to {run_dir}"
    except Exception as e:
        return "", f"❌ Agent 1 failed: {e}"


def run_single_agent_2(api_key, job_description):
    run_dir = _session.get("run_output_dir")
    if not run_dir:
        run_dir = str(make_run_dir(_ROOT / "outputs", "manual_run"))
        _session["run_output_dir"] = run_dir
        _setup_run_logging(Path(run_dir))
    try:
        result = run_agent_2(api_key, job_description, Path(run_dir))
        _session["agent_2_output"] = result
        return result, f"✅ Agent 2 complete — saved to {run_dir}"
    except Exception as e:
        return "", f"❌ Agent 2 failed: {e}"


def run_single_agent_3(api_key, company_name):
    run_dir = _session.get("run_output_dir")
    if not run_dir:
        run_dir = str(make_run_dir(_ROOT / "outputs", "manual_run"))
        _session["run_output_dir"] = run_dir
        _setup_run_logging(Path(run_dir))
    try:
        result = run_agent_3(api_key, company_name, Path(run_dir))
        _session["agent_3_output"] = result
        return result, f"✅ Agent 3 complete — saved to {run_dir}"
    except Exception as e:
        return "", f"❌ Agent 3 failed: {e}"


def run_single_agent_4(api_key):
    run_dir = _session.get("run_output_dir")
    if not run_dir:
        run_dir = str(make_run_dir(_ROOT / "outputs", "manual_run"))
        _session["run_output_dir"] = run_dir
        _setup_run_logging(Path(run_dir))

    a1 = _session["agent_1_output"]
    a2 = _session["agent_2_output"]
    a3 = _session["agent_3_output"]
    if not all([a1, a2, a3]):
        return "", "⚠️  Agent 4 needs Agents 1, 2, 3 to have run first"
    try:
        result = run_agent_4(api_key, a1, a3, a2, Path(run_dir))
        _session["agent_4_output"] = result
        return result, f"✅ Agent 4 complete — saved to {run_dir}"
    except Exception as e:
        return "", f"❌ Agent 4 failed: {e}"


def run_single_agent_5(api_key):
    run_dir = _session.get("run_output_dir")
    if not run_dir:
        run_dir = str(make_run_dir(_ROOT / "outputs", "manual_run"))
        _session["run_output_dir"] = run_dir
        _setup_run_logging(Path(run_dir))

    a4 = _session["agent_4_output"]
    if not a4:
        return "", "⚠️  Agent 5 needs Agent 4 to have run first"
    try:
        result = run_agent_5(api_key, a4, Path(run_dir))
        _session["agent_5_output"] = result
        return result, f"✅ Agent 5 complete — saved to {run_dir}"
    except Exception as e:
        return "", f"❌ Agent 5 failed: {e}"


def run_single_agent_6(api_key):
    run_dir = _session.get("run_output_dir")
    if not run_dir:
        run_dir = str(make_run_dir(_ROOT / "outputs", "manual_run"))
        _session["run_output_dir"] = run_dir
        _setup_run_logging(Path(run_dir))

    a5 = _session["agent_5_output"]
    if not a5:
        return "", "⚠️  Agent 6 needs Agent 5 to have run first"
    try:
        result = run_agent_6(api_key, a5, Path(run_dir))
        _session["agent_6_output"] = result
        return result, f"✅ Agent 6 complete — saved to {run_dir}"
    except Exception as e:
        return "", f"❌ Agent 6 failed: {e}"


# ── Pipeline Generator ────────────────────────────────────────────────────────
def run_pipeline(api_key: str, job_description: str, company_name: str):
    """
    Generator function that runs the full 6-agent LangGraph pipeline
    and yields UI updates after each agent completes.

    Yields tuples of:
        (status_text, out1, out2, out3, out4, out5, out6, download_update)
    matching the 8 Gradio output components defined in build_ui().
    """
    run_dir = make_run_dir(_ROOT / "outputs", company_name.strip())
    _session["run_output_dir"] = str(run_dir)
    _setup_run_logging(run_dir)  
    final_path = run_dir / "final_cover_letter.md"

    # ── Input validation ──────────────────────────────────────────────────
    if not api_key or not api_key.strip():
        yield ("⚠️ Please enter your Gemini API key in the field above.",
               "", "", "", "", "", "", gr.update(visible=False))
        return

    if not job_description or not job_description.strip():
        yield ("⚠️ Please paste the Job Description before clicking Generate.",
               "", "", "", "", "", "", gr.update(visible=False))
        return

    if not company_name or not company_name.strip():
        yield ("⚠️ Please enter the Company Name before clicking Generate.",
               "", "", "", "", "", "", gr.update(visible=False))
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
        "company_name":          company_name.strip(),
        "run_output_dir":        str(run_dir),
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
        for state_snapshot in graph.stream(initial_state, stream_mode="values"):
            updated = False

            for i, key in enumerate(AGENT_STATE_KEYS):
                value = state_snapshot.get(key, "")
                if value and not captured[i]:
                    outputs[i] = value
                    captured[i] = True
                    updated = True

                    # ── Back-fill session so individual buttons work immediately ──
                    _session[_SESSION_KEYS[i]] = value

                    # Build status message
                    next_idx = i + 1
                    if next_idx < 6:
                        next_label = AGENT_LABELS[next_idx]
                        status = (
                            f"✅ {AGENT_LABELS[i]} — Complete\n"
                            f"🔄 Now running: {next_label}…"
                        )
                        if next_idx == 2:
                            status += "\n⏳ Web search agent — may take 3–5 minutes."
                    else:
                        status = "✅ All 6 agents complete! Your cover letter is ready below."

                    download_update = (
                        gr.update(value=str(final_path), visible=True)
                        if i == 5 and final_path.exists()
                        else gr.update(visible=False)
                    )
                    yield (status, *outputs, download_update)
                    break

            if all(captured) and not updated:
                break

        # ── Handle any accumulated errors ─────────────────────────────────
        errors = state_snapshot.get("errors", [])  # type: ignore[possibly-undefined]
        if errors:
            error_lines = "\n".join(f"  • {e}" for e in errors)
            status = f"✅ Pipeline complete (with errors):\n{error_lines}"

        # ── Final yield with download button ──────────────────────────────
        download_update = (
            gr.update(value=str(final_path), visible=True)
            if final_path.exists()
            else gr.update(visible=False)
        )
        yield (status, *outputs, download_update)

    except Exception as exc:
        # ── FIX: preserve already-rendered outputs — do NOT wipe them ────
        completed = sum(captured)
        yield (
            f"🛑 Pipeline stopped: {exc}\n\n"
            f"✅ Agents 1–{completed} completed successfully — outputs saved to disk.\n"
            f"▶ Use the individual agent buttons above to re-run only the failed agent.",
            *outputs,                  # keep what was already rendered
            gr.update(visible=False),
        )
        return


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
                company_name_input = gr.Textbox(
                    label="🏢 Company Name",
                    placeholder="e.g. Siemens, Allianz, Fraunhofer, BMW...",
                    lines=1,
                    info="Exact company name — used by Agent 3 for culture research.",
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

        gr.Markdown("### ▶ Run Individual Agents")
        gr.Markdown("*Use these if the pipeline failed or you want to rerun a specific agent. Outputs from previous agents are read from the in-memory session (populated automatically as the pipeline runs).*")

        with gr.Row():
            btn_a1 = gr.Button("① Business Problem",  variant="secondary", size="sm")
            btn_a2 = gr.Button("② CV Skills",          variant="secondary", size="sm")
            btn_a3 = gr.Button("③ Company Culture",    variant="secondary", size="sm")
            btn_a4 = gr.Button("④ Cover Points",       variant="secondary", size="sm")
            btn_a5 = gr.Button("⑤ Organise",           variant="secondary", size="sm")
            btn_a6 = gr.Button("⑥ Write Letter",       variant="secondary", size="sm")

        agent_status_box = gr.Textbox(label="Agent Status", interactive=False, lines=2)

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
            inputs=[api_key_input, jd_input, company_name_input],
            outputs=[status_box, *tab_outputs, download_file],
            show_progress="hidden",
        )

        btn_a1.click(run_single_agent_1, inputs=[api_key_input, jd_input],           outputs=[tab_outputs[0], agent_status_box])
        btn_a2.click(run_single_agent_2, inputs=[api_key_input, jd_input],           outputs=[tab_outputs[1], agent_status_box])
        btn_a3.click(run_single_agent_3, inputs=[api_key_input, company_name_input], outputs=[tab_outputs[2], agent_status_box])
        btn_a4.click(run_single_agent_4, inputs=[api_key_input],                     outputs=[tab_outputs[3], agent_status_box])
        btn_a5.click(run_single_agent_5, inputs=[api_key_input],                     outputs=[tab_outputs[4], agent_status_box])
        btn_a6.click(run_single_agent_6, inputs=[api_key_input],                     outputs=[tab_outputs[5], agent_status_box])

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
