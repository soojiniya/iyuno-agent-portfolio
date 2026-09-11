import streamlit as st

from app import AgentConfigurationError, run_agent


def run_agent_once(user_task, agent_runner=run_agent):
    return agent_runner(
        user_task,
        progress_callback=update_progress,
        include_steps=True,
        verbose=False,
    )


def update_progress(step_name, status):
    step_order = ["요청 분석", "초안 생성", "품질 검토"]

    if "completed_steps" not in st.session_state:
        st.session_state.completed_steps = set()

    if status == "running":
        st.session_state.status_placeholder.info(f"현재 단계: {step_name}")

    if status == "complete":
        st.session_state.completed_steps.add(step_name)
        st.session_state.progress_placeholder.progress(
            len(st.session_state.completed_steps) / len(step_order)
        )
        st.session_state.status_placeholder.success(f"완료된 단계: {step_name}")


st.set_page_config(
    page_title="IYUNO AI Agent",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 IYUNO AI Agent")

st.write(
    "사용자의 요청을 분석하고, 초안을 작성한 뒤 "
    "품질을 검토하여 최종 결과를 생성합니다."
)

st.divider()

user_task = st.text_area(
    "처리할 작업을 입력하세요",
    placeholder="예: 고객의 환불 문의에 답변하는 이메일을 작성해줘.",
    height=150,
)

if st.button(
    "Agent 실행",
    type="primary",
    use_container_width=True,
):
    if not user_task.strip():
        st.warning("처리할 작업을 먼저 입력해주세요.")

    else:
        try:
            st.session_state.completed_steps = set()
            st.session_state.progress_placeholder = st.progress(0)
            st.session_state.status_placeholder = st.empty()

            result = run_agent_once(user_task)

            st.success("작업이 완료되었습니다.")

            final_tab, steps_tab = st.tabs(["최종 결과", "Agent 단계"])

            with final_tab:
                st.subheader("최종 결과")
                st.markdown(result.final_answer)

            with steps_tab:
                for step in result.steps:
                    with st.expander(step.name):
                        st.caption(step.description)
                        st.markdown(step.output)

        except AgentConfigurationError as e:
            st.error(str(e))

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
