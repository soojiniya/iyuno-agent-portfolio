import os
import re
from dataclasses import dataclass
from typing import List

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")


@dataclass
class AgentStep:
    name: str
    description: str
    output: str


@dataclass
class AgentRunResult:
    task: str
    steps: List[AgentStep]
    final_answer: str


class AgentConfigurationError(RuntimeError):
    pass


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AgentConfigurationError(
            "OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인해주세요."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AgentConfigurationError(
            "openai 패키지가 설치되어 있지 않습니다. requirements.txt를 설치해주세요."
        ) from exc

    return OpenAI(api_key=api_key)


def normalize_markdown_escapes(text):
    """
    Convert over-escaped Markdown returned by the model into renderable Markdown.

    Some model responses include backslashes before Markdown control characters,
    for example '\\*\\*title\\*\\*'. Streamlit then renders the asterisks as
    literal text instead of bold syntax. This keeps the cleanup in the Agent
    output layer so CLI, tests, and web UI all receive the same final answer.
    """
    if not text:
        return text

    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>])", r"\1", text)


def ask_ai(instructions, user_input, *, client=None, model=None):
    active_client = client or get_client()

    response = active_client.responses.create(
        model=model or DEFAULT_MODEL,
        instructions=instructions,
        input=user_input,
    )
    return response.output_text


def _notify(progress_callback, step_name, status):
    if progress_callback:
        progress_callback(step_name, status)


def run_agent(task, *, progress_callback=None, include_steps=False, client=None, verbose=True):
    if not task or not task.strip():
        raise ValueError("처리할 작업을 입력해주세요.")

    steps = []

    if verbose:
        print("\n[1] 요청 분석 중...")
    _notify(progress_callback, "요청 분석", "running")

    analysis = ask_ai(
        """
        You are a task analysis agent.
        Analyze the user's request and identify:
        1. The main goal
        2. Important requirements
        3. A short execution plan
        Keep the response concise.
        Write Markdown normally. Do not escape Markdown characters such as *, #, [, or ].
        """,
        task,
        client=client,
    )
    analysis = normalize_markdown_escapes(analysis)
    steps.append(AgentStep("요청 분석", "사용자 요청의 목표와 요구사항을 분석합니다.", analysis))
    _notify(progress_callback, "요청 분석", "complete")

    if verbose:
        print("\n[2] 초안 생성 중...")
    _notify(progress_callback, "초안 생성", "running")

    draft = ask_ai(
        """
        You are an execution agent.
        Complete the user's task based on the analysis provided.
        Produce a useful and professional result.
        Write Markdown normally. Do not escape Markdown characters such as *, #, [, or ].
        """,
        f"""
        User request:
        {task}

        Task analysis:
        {analysis}
        """,
        client=client,
    )
    draft = normalize_markdown_escapes(draft)
    steps.append(AgentStep("초안 생성", "분석 결과를 바탕으로 초안을 작성합니다.", draft))
    _notify(progress_callback, "초안 생성", "complete")

    if verbose:
        print("\n[3] 결과 검토 중...")
    _notify(progress_callback, "품질 검토", "running")

    final_result = ask_ai(
        """
        You are a quality review agent.
        Review the draft for accuracy, clarity, and completeness.
        Fix any problems and return only the improved final answer.
        Write Markdown normally. Do not escape Markdown characters such as *, #, [, or ].
        """,
        f"""
        Original request:
        {task}

        Draft:
        {draft}
        """,
        client=client,
    )
    final_result = normalize_markdown_escapes(final_result)
    steps.append(AgentStep("품질 검토", "초안을 검토하고 최종 답변으로 개선합니다.", final_result))
    _notify(progress_callback, "품질 검토", "complete")

    result = AgentRunResult(task=task, steps=steps, final_answer=final_result)
    if include_steps:
        return result

    return result.final_answer


if __name__ == "__main__":
    print("=== IYUNO Agent Portfolio ===")

    user_task = input("\n처리할 작업을 입력하세요: ")

    result = run_agent(user_task)

    print("\n=== 최종 결과 ===")
    print(result)
