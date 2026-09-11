import os
import streamlit as st
from html import escape

from app import AgentConfigurationError, AgentRunResult, AgentStep, run_agent


AGENT_STEPS = ["요청 분석", "초안 생성", "품질 검토"]
STEP_LABELS = {
    "요청 분석": ("01", "Analyze"),
    "초안 생성": ("02", "Draft"),
    "품질 검토": ("03", "Review"),
}

PUBLIC_DEMO_ONLY_ENV = "IYUNO_PUBLIC_DEMO_ONLY"
STREAMLIT_SHARING_MODE_ENV = "STREAMLIT_SHARING_MODE"


def apply_theme():
    st.markdown(
        """
        <style>
        :root {
            --iyuno-black: #0a0a0a;
            --iyuno-charcoal: #111111;
            --iyuno-dark-gray: #181818;
            --iyuno-gray-800: #242424;
            --iyuno-gray-700: #333333;
            --iyuno-gray-500: #737373;
            --iyuno-gray-300: #d4d4d4;
            --iyuno-gray-200: #e5e5e5;
            --iyuno-white: #fafafa;
            --iyuno-coral: #ff4b4b;
            --iyuno-coral-hover: #f04444;
            --iyuno-coral-active: #e63f3f;
        }

        .stApp {
            background: var(--iyuno-black);
            color: var(--iyuno-white);
        }

        .block-container {
            max-width: 900px;
            padding-top: 4.5rem;
            padding-bottom: 5rem;
        }

        section[data-testid="stSidebar"] {
            background: var(--iyuno-charcoal);
            border-right: 1px solid var(--iyuno-gray-800);
        }

        h1 {
            font-size: clamp(2.7rem, 7vw, 5rem);
            font-weight: 800;
            letter-spacing: 0;
            line-height: 0.95;
            margin-bottom: 1rem;
        }

        .iyuno-subtitle {
            color: #a3a3a3;
            font-size: 1.02rem;
            line-height: 1.65;
            margin: 0 0 1.35rem;
            max-width: 620px;
        }

        .iyuno-hero {
            padding: 1.4rem 0 2.2rem;
        }

        .iyuno-divider {
            height: 1px;
            background: var(--iyuno-gray-800);
            margin: 0.35rem 0 2.35rem;
        }

        .stButton > button[kind="primary"] {
            background: var(--iyuno-coral);
            border: 1px solid var(--iyuno-coral);
            color: var(--iyuno-white);
            border-radius: 0.35rem;
            box-shadow: none;
            min-height: 3rem;
            font-weight: 650;
            transition: background 140ms ease, border-color 140ms ease, color 140ms ease;
        }

        .stButton > button[kind="primary"]:hover {
            background: var(--iyuno-coral-hover);
            border-color: var(--iyuno-coral-hover);
            color: var(--iyuno-white);
            box-shadow: none;
        }

        .stButton > button[kind="primary"]:focus,
        .stButton > button[kind="primary"]:active {
            background: var(--iyuno-coral-active);
            border-color: var(--iyuno-coral-active);
            color: var(--iyuno-white);
            box-shadow: none;
            outline: none;
        }

        div[data-testid="stTextArea"] textarea {
            background: var(--iyuno-dark-gray);
            border: 1px solid var(--iyuno-gray-700);
            border-radius: 0.35rem;
            color: var(--iyuno-white);
            caret-color: var(--iyuno-white);
            line-height: 1.65;
        }

        div[data-testid="stTextArea"] textarea:hover {
            border-color: var(--iyuno-gray-500) !important;
        }

        div[data-testid="stTextArea"] textarea:focus,
        div[data-testid="stTextArea"] textarea:focus-visible {
            border-color: var(--iyuno-white) !important;
            box-shadow: none !important;
            outline: none !important;
        }

        div[data-testid="stTextArea"] div:focus-within {
            border-color: var(--iyuno-white) !important;
            box-shadow: none !important;
            outline: none !important;
        }

        div[data-testid="stTextArea"] textarea[aria-invalid="false"]:focus,
        div[data-testid="stTextArea"] textarea[aria-invalid="false"]:focus-visible {
            border-color: var(--iyuno-white) !important;
            box-shadow: none !important;
            outline: none !important;
        }

        div[data-testid="stTextArea"] label p {
            color: var(--iyuno-gray-300);
            font-size: 0.78rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }

        div[data-testid="stProgress"] > div > div > div {
            background-color: var(--iyuno-gray-300);
            height: 4px;
        }

        div[data-testid="stProgress"] > div > div {
            background-color: var(--iyuno-gray-800);
            height: 4px;
            overflow: hidden;
        }

        div[data-testid="stProgress"] {
            margin: 1.35rem 0 0.65rem;
            height: 4px;
        }

        .iyuno-mode-badge {
            display: inline-flex;
            align-items: center;
            width: fit-content;
            background: var(--iyuno-dark-gray);
            border: 1px solid var(--iyuno-gray-700);
            border-radius: 0.28rem;
            color: var(--iyuno-gray-300);
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            line-height: 1;
            padding: 0.42rem 0.55rem;
            margin: 0.3rem 0 0;
            text-transform: uppercase;
        }

        .iyuno-status {
            background: var(--iyuno-dark-gray);
            border: 1px solid var(--iyuno-gray-700);
            border-radius: 0.35rem;
            color: var(--iyuno-gray-300);
            padding: 0.72rem 0.85rem;
            margin: 0.55rem 0 0.9rem;
        }

        .iyuno-workflow {
            display: flex;
            flex-wrap: nowrap;
            align-items: center;
            width: fit-content;
            max-width: 100%;
            gap: 0.55rem;
            margin: 1rem 0 0.75rem;
        }

        .iyuno-workflow__step {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--iyuno-white);
            font-size: 0.86rem;
            font-weight: 560;
            white-space: nowrap;
        }

        .iyuno-workflow__step.is-active,
        .iyuno-workflow__step.is-complete {
            color: var(--iyuno-white);
        }

        .iyuno-workflow__badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.85rem;
            height: 1.85rem;
            border: 1px solid var(--iyuno-gray-700);
            border-radius: 999px;
            color: var(--iyuno-gray-300);
            font-size: 0.72rem;
            letter-spacing: 0.02em;
        }

        .iyuno-workflow__line {
            flex: 0 0 44px;
            height: 1px;
            background: var(--iyuno-gray-800);
        }

        .iyuno-workflow__check {
            color: var(--iyuno-white);
            margin-left: 0.1rem;
        }

        .iyuno-workflow__caption {
            color: var(--iyuno-gray-500);
            font-size: 0.78rem;
            margin: 0.1rem 0 2.3rem;
        }

        .iyuno-result-heading {
            color: var(--iyuno-white);
            font-size: 1.65rem;
            font-weight: 720;
            letter-spacing: 0;
            margin: 2.1rem 0 1.35rem;
        }

        div[data-testid="stTabs"] {
            --primary-color: var(--iyuno-coral) !important;
        }

        div[data-testid="stTabs"] button[role="tab"],
        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            color: var(--iyuno-gray-500) !important;
        }

        div[data-testid="stTabs"] button[role="tab"] *,
        div[data-testid="stTabs"] button[data-baseweb="tab"] * {
            color: inherit !important;
        }

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--iyuno-coral) !important;
            border-bottom-color: var(--iyuno-coral) !important;
            box-shadow: inset 0 -1px 0 var(--iyuno-coral) !important;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: var(--iyuno-coral) !important;
            height: 1px;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-border"] {
            background-color: var(--iyuno-gray-800) !important;
        }

        div[data-testid="stTabs"] [role="tablist"] {
            gap: 1rem;
            margin-top: 0.4rem;
        }

        div[data-testid="stTabs"] div[role="tabpanel"] {
            padding-top: 1.2rem;
        }

        div[data-testid="stCheckbox"] {
            --primary-color: var(--iyuno-gray-300) !important;
        }

        div[data-testid="stCheckbox"] input {
            accent-color: var(--iyuno-gray-300);
        }

        div[data-testid="stCheckbox"] [data-checked="true"],
        div[data-testid="stCheckbox"] input:checked + div {
            background-color: var(--iyuno-gray-300) !important;
            border-color: var(--iyuno-gray-300) !important;
        }

        div[data-testid="stExpander"] {
            border-color: var(--iyuno-gray-800);
            background: var(--iyuno-dark-gray);
            border-radius: 0.35rem;
        }

        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] p {
            color: var(--iyuno-gray-300);
        }

        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stMarkdownContainer"] li {
            line-height: 1.85;
            color: var(--iyuno-gray-200);
        }

        div[data-testid="stMarkdownContainer"] strong {
            color: var(--iyuno-white);
        }

        hr {
            border-color: var(--iyuno-gray-800);
        }

        @media (max-width: 640px) {
            .block-container {
                padding-top: 3rem;
            }

            .iyuno-workflow {
                gap: 0.5rem;
            }

            .iyuno-workflow__line {
                flex-basis: 24px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_status_box(message, tone="notice", target=None):
    html = f'<div class="iyuno-status iyuno-status--{tone}">{escape(message)}</div>'
    if target is not None:
        target.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


def render_mode_badge(message):
    st.markdown(
        f'<div class="iyuno-mode-badge">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def env_flag_enabled(name):
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def is_public_demo_only():
    return env_flag_enabled(PUBLIC_DEMO_ONLY_ENV) or bool(os.getenv(STREAMLIT_SHARING_MODE_ENV))


def get_demo_mode(public_demo_only):
    selected_demo_mode = st.sidebar.checkbox(
        "데모 모드 (API 사용 안 함)",
        value=True,
        disabled=public_demo_only,
        help="공개 배포 환경에서는 API 크레딧 보호를 위해 데모 모드만 사용할 수 있습니다."
        if public_demo_only
        else None,
    )

    return True if public_demo_only else selected_demo_mode


def render_workflow_status(current_step=None, completed=False, target=None):
    completed_steps = st.session_state.get("completed_steps", set())
    parts = ['<div class="iyuno-workflow">']

    for index, step_name in enumerate(AGENT_STEPS):
        number, label = STEP_LABELS[step_name]
        classes = ["iyuno-workflow__step"]

        if completed or step_name in completed_steps:
            classes.append("is-complete")

        if current_step == step_name:
            classes.append("is-active")

        check = (
            '<span class="iyuno-workflow__check">✓</span>'
            if completed and index == len(AGENT_STEPS) - 1
            else ""
        )
        parts.append(
            f'<span class="{" ".join(classes)}">'
            f'<span class="iyuno-workflow__badge">{number}</span>'
            f'<span>{label}</span>{check}</span>'
        )

        if index < len(AGENT_STEPS) - 1:
            parts.append('<span class="iyuno-workflow__line"></span>')

    parts.append("</div>")

    if completed:
        parts.append('<div class="iyuno-workflow__caption">Workflow completed</div>')

    html = "".join(parts)

    if target is not None:
        target.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


def run_agent_once(user_task, agent_runner=run_agent):
    return agent_runner(
        user_task,
        progress_callback=update_progress,
        include_steps=True,
        verbose=False,
    )


def create_demo_result(user_task):
    analysis = """
**요청 분석**

- 고객은 배송 지연 상황에 대해 문의하고 있습니다.
- 답변에는 정중한 사과, 현재 배송 현황 안내, 향후 조치가 포함되어야 합니다.
- 고객이 안심할 수 있도록 명확하고 공손한 이메일 형식으로 작성합니다.
"""

    draft = """
**초안**

안녕하세요, 고객님.

배송이 지연되어 불편을 드려 죄송합니다. 현재 주문 상품은 배송사 물류 처리 단계에 있으며, 확인되는 즉시 추가 안내를 드리겠습니다.

감사합니다.
"""

    review = """
**품질 검토**

- 사과 표현이 포함되어 있습니다.
- 배송 현황과 다음 조치가 명확하게 들어 있습니다.
- 고객 응대 이메일로 사용할 수 있도록 문장을 더 정중하고 완성도 있게 다듬었습니다.
"""

    final_answer = """
**제목: 배송 지연 관련 안내드립니다**

안녕하세요, 고객님.

먼저 주문하신 상품의 배송이 지연되어 불편을 드린 점 진심으로 사과드립니다.

현재 고객님의 주문 상품은 배송사 물류 처리 단계에서 확인 중이며, 정확한 이동 현황을 확인하는 대로 추가 안내드리겠습니다. 필요 시 배송사와의 확인을 통해 예상 도착 일정도 함께 안내드리겠습니다.

기다려주셔서 감사드리며, 최대한 빠르게 배송 상황을 확인해 불편을 줄일 수 있도록 하겠습니다.

감사합니다.  
고객지원팀 드림
"""

    return AgentRunResult(
        task=user_task,
        steps=[
            AgentStep("요청 분석", "사용자 요청의 목표와 요구사항을 분석합니다.", analysis),
            AgentStep("초안 생성", "분석 결과를 바탕으로 초안을 작성합니다.", draft),
            AgentStep("품질 검토", "초안을 검토하고 최종 답변으로 개선합니다.", review),
        ],
        final_answer=final_answer,
    )


def run_demo_agent(user_task, progress_callback=None):
    active_progress_callback = progress_callback or update_progress

    for step_name in AGENT_STEPS:
        active_progress_callback(step_name, "running")
        active_progress_callback(step_name, "complete")

    return create_demo_result(user_task)


def update_progress(step_name, status):
    if "completed_steps" not in st.session_state:
        st.session_state.completed_steps = set()

    if status == "running":
        render_workflow_status(current_step=step_name, target=st.session_state.status_placeholder)

    if status == "complete":
        st.session_state.completed_steps.add(step_name)
        st.session_state.progress_placeholder.progress(
            len(st.session_state.completed_steps) / len(AGENT_STEPS)
        )
        render_workflow_status(
            completed=len(st.session_state.completed_steps) == len(AGENT_STEPS),
            target=st.session_state.status_placeholder,
        )


def render_result(result):
    final_tab, steps_tab = st.tabs(["최종 결과", "Agent 단계"])

    with final_tab:
        st.markdown('<div class="iyuno-result-heading">최종 결과</div>', unsafe_allow_html=True)
        st.markdown(result.final_answer)

    with steps_tab:
        for step in result.steps:
            with st.expander(step.name):
                st.caption(step.description)
                st.markdown(step.output)


st.set_page_config(
    page_title="IYUNO AI Agent",
    page_icon="🤖",
    layout="centered",
)

apply_theme()

st.markdown('<div class="iyuno-hero">', unsafe_allow_html=True)
st.title("IYUNO AI Agent")
st.markdown(
    '<div class="iyuno-subtitle">Multi-step AI agent for analysis, drafting and quality review</div>',
    unsafe_allow_html=True,
)

public_demo_only = is_public_demo_only()
demo_mode = get_demo_mode(public_demo_only)

if demo_mode:
    render_mode_badge("DEMO MODE · API CREDIT 0")
else:
    render_mode_badge("LIVE MODE · API CREDIT USED")

if public_demo_only:
    st.caption("Public deployment: Live Mode is disabled to protect API credits.")

st.markdown('</div><div class="iyuno-divider"></div>', unsafe_allow_html=True)

user_task = st.text_area(
    "작업 요청",
    placeholder="예: 고객의 환불 문의에 답변하는 이메일을 작성해줘.",
    height=150,
)

if st.button(
    "Agent 실행",
    type="primary",
    use_container_width=True,
):
    if not user_task.strip():
        render_status_box("처리할 작업을 먼저 입력해주세요.", tone="notice")

    else:
        try:
            st.session_state.completed_steps = set()
            st.session_state.progress_placeholder = st.progress(0)
            st.session_state.status_placeholder = st.empty()

            if demo_mode:
                result = run_demo_agent(user_task)
            else:
                result = run_agent_once(user_task)

            render_result(result)

        except AgentConfigurationError as e:
            render_status_box(str(e), tone="active")

        except Exception as e:
            render_status_box(f"오류가 발생했습니다: {e}", tone="active")
