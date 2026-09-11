import importlib.util
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


def make_fake_streamlit(button_clicked, demo_mode=True):
    fake_st = types.ModuleType("streamlit")
    fake_st.session_state = SessionState()
    fake_st.sidebar = SimpleNamespace(
        checkbox=lambda *args, **kwargs: demo_mode,
    )
    fake_st.set_page_config = lambda *args, **kwargs: None
    fake_st.title = lambda *args, **kwargs: None
    fake_st.write = lambda *args, **kwargs: None
    fake_st.info = lambda *args, **kwargs: None
    fake_st.divider = lambda *args, **kwargs: None
    fake_st.text_area = lambda *args, **kwargs: "테스트 작업"
    fake_st.button = lambda *args, **kwargs: button_clicked
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


def import_web_app_with_fakes(button_clicked, fake_runner, demo_mode=True):
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

    original_streamlit = sys.modules.get("streamlit")
    original_app = sys.modules.get("app")
    sys.modules["streamlit"] = make_fake_streamlit(button_clicked, demo_mode=demo_mode)
    sys.modules["app"] = fake_app

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

        def fake_runner(task, progress_callback=None, include_steps=False, verbose=True):
            calls.append(
                {
                    "task": task,
                    "include_steps": include_steps,
                    "verbose": verbose,
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


if __name__ == "__main__":
    unittest.main()
