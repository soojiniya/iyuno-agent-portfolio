import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_APP_PATH = ROOT_DIR / "src" / "web_app.py"


class SessionState(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class NoOpContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def caption(self, *args, **kwargs):
        pass

    def markdown(self, *args, **kwargs):
        pass


class Placeholder:
    def markdown(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def success(self, *args, **kwargs):
        pass

    def progress(self, *args, **kwargs):
        pass


def make_fake_streamlit(
    button_clicked,
    demo_mode=True,
    use_rag=False,
    use_tools=False,
    feedback_submitted=False,
):
    fake_st = types.ModuleType("streamlit")
    fake_st.session_state = SessionState()
    fake_st.sidebar = SimpleNamespace(
        checkbox=lambda *args, **kwargs: demo_mode,
    )
    checkbox_values = [use_rag, use_tools]

    def checkbox(*args, **kwargs):
        return checkbox_values.pop(0) if checkbox_values else False

    fake_st.set_page_config = lambda *args, **kwargs: None
    fake_st.title = lambda *args, **kwargs: None
    fake_st.write = lambda *args, **kwargs: None
    fake_st.info = lambda *args, **kwargs: None
    fake_st.divider = lambda *args, **kwargs: None
    fake_st.text_area = lambda *args, **kwargs: "테스트 작업"
    fake_st.checkbox = checkbox
    fake_st.button = lambda label, *args, **kwargs: button_clicked if "Agent" in label else False
    fake_st.form = lambda *args, **kwargs: NoOpContext()
    fake_st.form_submit_button = lambda *args, **kwargs: feedback_submitted
    fake_st.radio = lambda *args, **kwargs: "도움됨"
    fake_st.warning = lambda *args, **kwargs: None
    fake_st.success = lambda *args, **kwargs: None
    fake_st.error = lambda *args, **kwargs: None
    fake_st.subheader = lambda *args, **kwargs: None
    fake_st.markdown = lambda *args, **kwargs: None
    fake_st.caption = lambda *args, **kwargs: None
    fake_st.progress = lambda *args, **kwargs: Placeholder()
    fake_st.empty = lambda *args, **kwargs: Placeholder()
    fake_st.tabs = lambda labels: [NoOpContext(), NoOpContext()]
    fake_st.expander = lambda *args, **kwargs: NoOpContext()
    return fake_st


def import_web_app_with_fakes(
    button_clicked,
    fake_runner,
    demo_mode=True,
    use_rag=False,
    use_tools=False,
    env=None,
    feedback_submitted=False,
    fake_save_feedback=None,
):
    class AgentStep:
        def __init__(self, name, description, output):
            self.name = name
            self.description = description
            self.output = output

    class AgentRunResult:
        def __init__(self, task, steps, final_answer):
            self.task = task
            self.steps = steps
            self.final_answer = final_answer

    fake_app = types.ModuleType("app")
    fake_app.AgentConfigurationError = RuntimeError
    fake_app.AgentRunResult = AgentRunResult
    fake_app.AgentStep = AgentStep
    fake_app.run_agent = fake_runner
    fake_app.run_rag_agent = fake_runner

    fake_feedback = types.ModuleType("feedback")

    class FeedbackRecord:
        def __init__(
            self,
            original_request,
            final_answer,
            use_rag,
            use_tools,
            rating,
            comment="",
            timestamp=None,
        ):
            self.original_request = original_request
            self.final_answer = final_answer
            self.use_rag = use_rag
            self.use_tools = use_tools
            self.rating = rating
            self.comment = comment
            self.timestamp = timestamp

    fake_feedback.FeedbackRecord = FeedbackRecord
    fake_feedback.save_feedback = fake_save_feedback or (lambda *args, **kwargs: 1)

    original_streamlit = sys.modules.get("streamlit")
    original_app = sys.modules.get("app")
    original_feedback = sys.modules.get("feedback")
    original_env = {}
    env = env or {}

    for key, value in env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    sys.modules["streamlit"] = make_fake_streamlit(
        button_clicked,
        demo_mode=demo_mode,
        use_rag=use_rag,
        use_tools=use_tools,
        feedback_submitted=feedback_submitted,
    )
    sys.modules["app"] = fake_app
    sys.modules["feedback"] = fake_feedback

    try:
        spec = importlib.util.spec_from_file_location("web_app_under_test", WEB_APP_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if original_streamlit is None:
            sys.modules.pop("streamlit", None)
        else:
            sys.modules["streamlit"] = original_streamlit

        if original_app is None:
            sys.modules.pop("app", None)
        else:
            sys.modules["app"] = original_app

        if original_feedback is None:
            sys.modules.pop("feedback", None)
        else:
            sys.modules["feedback"] = original_feedback

        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


class WebAppExecutionTest(unittest.TestCase):
    def test_demo_mode_button_click_does_not_call_agent_runner(self):
        calls = []

        def fake_runner(*args, **kwargs):
            calls.append((args, kwargs))

        import_web_app_with_fakes(
            button_clicked=True,
            fake_runner=fake_runner,
            demo_mode=True,
        )

        self.assertEqual(calls, [])

    def test_real_mode_button_click_calls_agent_runner_once(self):
        calls = []

        def fake_runner(task, progress_callback=None, include_steps=False, verbose=True, use_tools=False):
            calls.append(
                {
                    "task": task,
                    "include_steps": include_steps,
                    "verbose": verbose,
                    "use_tools": use_tools,
                }
            )
            progress_callback("요청 분석", "running")
            progress_callback("요청 분석", "complete")
            return SimpleNamespace(final_answer="final", steps=[])

        import_web_app_with_fakes(
            button_clicked=True,
            fake_runner=fake_runner,
            demo_mode=False,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["task"], "테스트 작업")
        self.assertTrue(calls[0]["include_steps"])
        self.assertFalse(calls[0]["verbose"])
        self.assertFalse(calls[0]["use_tools"])

    def test_public_demo_only_mode_never_calls_agent_runner(self):
        calls = []

        def fake_runner(*args, **kwargs):
            calls.append((args, kwargs))

        import_web_app_with_fakes(
            button_clicked=True,
            fake_runner=fake_runner,
            demo_mode=False,
            env={"IYUNO_PUBLIC_DEMO_ONLY": "true"},
        )

        self.assertEqual(calls, [])

    def test_public_demo_only_mode_with_rag_never_calls_agent_runner(self):
        calls = []

        def fake_runner(*args, **kwargs):
            calls.append((args, kwargs))

        import_web_app_with_fakes(
            button_clicked=True,
            fake_runner=fake_runner,
            demo_mode=False,
            use_rag=True,
            env={"IYUNO_PUBLIC_DEMO_ONLY": "true"},
        )

        self.assertEqual(calls, [])

    def test_live_rag_mode_button_click_calls_runner_once(self):
        calls = []

        def fake_runner(task, progress_callback=None, include_steps=False, verbose=True, use_tools=False):
            calls.append(
                {
                    "task": task,
                    "include_steps": include_steps,
                    "verbose": verbose,
                    "use_tools": use_tools,
                }
            )
            progress_callback("요청 분석", "running")
            progress_callback("요청 분석", "complete")
            return SimpleNamespace(final_answer="rag final", steps=[])

        import_web_app_with_fakes(
            button_clicked=True,
            fake_runner=fake_runner,
            demo_mode=False,
            use_rag=True,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["task"], "테스트 작업")
        self.assertTrue(calls[0]["include_steps"])
        self.assertFalse(calls[0]["verbose"])
        self.assertFalse(calls[0]["use_tools"])

    def test_live_tool_mode_passes_use_tools_to_runner(self):
        calls = []

        def fake_runner(task, progress_callback=None, include_steps=False, verbose=True, use_tools=False):
            calls.append(
                {
                    "task": task,
                    "include_steps": include_steps,
                    "verbose": verbose,
                    "use_tools": use_tools,
                }
            )
            progress_callback("요청 분석", "running")
            progress_callback("요청 분석", "complete")
            return SimpleNamespace(final_answer="tool final", steps=[])

        import_web_app_with_fakes(
            button_clicked=True,
            fake_runner=fake_runner,
            demo_mode=False,
            use_tools=True,
        )

        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["use_tools"])

    def test_streamlit_cloud_mode_never_calls_agent_runner(self):
        calls = []

        def fake_runner(*args, **kwargs):
            calls.append((args, kwargs))

        import_web_app_with_fakes(
            button_clicked=True,
            fake_runner=fake_runner,
            demo_mode=False,
            env={"STREAMLIT_SHARING_MODE": "streamlit_app"},
        )

        self.assertEqual(calls, [])

    def test_regular_rerun_without_button_click_does_not_call_agent_runner(self):
        calls = []

        def fake_runner(*args, **kwargs):
            calls.append((args, kwargs))

        import_web_app_with_fakes(
            button_clicked=False,
            fake_runner=fake_runner,
            demo_mode=False,
        )

        self.assertEqual(calls, [])

    def test_feedback_submit_saves_once_and_does_not_call_agent_runner_in_demo_mode(self):
        runner_calls = []
        feedback_calls = []

        def fake_runner(*args, **kwargs):
            runner_calls.append((args, kwargs))

        def fake_save_feedback(record):
            feedback_calls.append(record)
            return len(feedback_calls)

        module = import_web_app_with_fakes(
            button_clicked=True,
            fake_runner=fake_runner,
            demo_mode=True,
            feedback_submitted=True,
            fake_save_feedback=fake_save_feedback,
        )
        module.render_feedback_form(module.create_demo_result("테스트 작업"))

        self.assertEqual(runner_calls, [])
        self.assertEqual(len(feedback_calls), 1)
        self.assertEqual(feedback_calls[0].rating, "helpful")


if __name__ == "__main__":
    unittest.main()
