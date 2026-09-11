import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from rag import format_citations, retrieve
from tools import format_tool_results, select_and_run_tools

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")
DEFAULT_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@dataclass
class AgentStep:
    name: str
    description: str
    output: str


@dataclass
class AgentState:
    original_request: str
    analysis: str = ""
    retrieved_context: str = ""
    tool_results: str = ""
    draft: str = ""
    review: str = ""
    final_answer: str = ""
    citations: str = ""

    def to_summary_markdown(self) -> str:
        return "\n".join(
            [
                "**State Summary**",
                "",
                f"- Original request: {summarize_text(self.original_request)}",
                f"- Analysis: {summarize_text(self.analysis)}",
                f"- Retrieved RAG context: {summarize_text(self.retrieved_context)}",
                f"- Tool execution result: {summarize_text(self.tool_results)}",
                f"- Draft: {summarize_text(self.draft)}",
                f"- Review: {summarize_text(self.review)}",
                f"- Final answer: {summarize_text(self.final_answer)}",
            ]
        )


@dataclass
class AgentRunResult:
    task: str
    steps: List[AgentStep]
    final_answer: str
    state: Optional[AgentState] = None


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


def summarize_text(text, *, max_length=180):
    if not text:
        return "not set"

    single_line = re.sub(r"\s+", " ", text).strip()
    if len(single_line) <= max_length:
        return single_line

    return f"{single_line[: max_length - 3]}..."


def ask_ai(instructions, user_input, *, client=None, model=None):
    active_client = client or get_client()

    response = active_client.responses.create(
        model=model or DEFAULT_MODEL,
        instructions=instructions,
        input=user_input,
    )
    return response.output_text


def embed_with_openai(texts, *, client=None, model=None):
    active_client = client or get_client()
    response = active_client.embeddings.create(
        model=model or DEFAULT_EMBEDDING_MODEL,
        input=list(texts),
    )
    return [item.embedding for item in response.data]


def _notify(progress_callback, step_name, status):
    if progress_callback:
        progress_callback(step_name, status)


def run_agent(task, *, progress_callback=None, include_steps=False, client=None, verbose=True, use_tools=False):
    if not task or not task.strip():
        raise ValueError("처리할 작업을 입력해주세요.")

    state = AgentState(original_request=task)
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
    state.analysis = analysis
    steps.append(AgentStep("요청 분석", "사용자 요청의 목표와 요구사항을 분석합니다.", analysis))
    _notify(progress_callback, "요청 분석", "complete")

    tool_context = ""
    if use_tools:
        tool_results = select_and_run_tools(task)
        tool_context = format_tool_results(tool_results)
        state.tool_results = tool_context
        steps.append(AgentStep("Tool Calling", "필요한 local tool을 선택하고 실행합니다.", tool_context))

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

        Tool results:
        {tool_context or "Tool calls disabled."}
        """,
        client=client,
    )
    draft = normalize_markdown_escapes(draft)
    state.draft = draft
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
    state.review = final_result
    state.final_answer = final_result
    steps.append(AgentStep("품질 검토", "초안을 검토하고 최종 답변으로 개선합니다.", final_result))
    _notify(progress_callback, "품질 검토", "complete")

    result = AgentRunResult(task=task, steps=steps, final_answer=final_result, state=state)
    if include_steps:
        return result

    return result.final_answer


def run_rag_agent(
    task,
    *,
    progress_callback=None,
    include_steps=False,
    client=None,
    verbose=True,
    data_dir=DEFAULT_DATA_DIR,
    top_k=3,
    use_tools=False,
):
    if not task or not task.strip():
        raise ValueError("처리할 작업을 입력해주세요.")

    state = AgentState(original_request=task)
    steps = []

    if verbose:
        print("\n[1] 요청 분석 및 문서 검색 중...")
    _notify(progress_callback, "요청 분석", "running")

    retrieved_results = retrieve(
        task,
        data_dir,
        lambda texts: embed_with_openai(texts, client=client),
        top_k=top_k,
    )
    context = "\n\n".join(
        f"[{index}] Source: {result.chunk.source}#chunk-{result.chunk.chunk_id}\n{result.chunk.text}"
        for index, result in enumerate(retrieved_results, start=1)
    )
    citations = format_citations(retrieved_results)
    state.retrieved_context = context or "No matching local documents were found."
    state.citations = citations

    analysis = ask_ai(
        """
        You are a task analysis agent using retrieved context.
        Analyze the user's request and the retrieved documents.
        Identify:
        1. The main goal
        2. Which retrieved sources are relevant
        3. A short execution plan
        Keep the response concise.
        Write Markdown normally. Do not escape Markdown characters such as *, #, [, or ].
        """,
        f"""
        User request:
        {task}

        Retrieved context:
        {context or "No matching local documents were found."}
        """,
        client=client,
    )
    analysis = normalize_markdown_escapes(analysis)
    state.analysis = analysis
    steps.append(AgentStep("요청 분석", "사용자 요청을 분석하고 관련 문서를 검색합니다.", analysis))
    _notify(progress_callback, "요청 분석", "complete")

    tool_context = ""
    if use_tools:
        tool_results = select_and_run_tools(task)
        tool_context = format_tool_results(tool_results)
        state.tool_results = tool_context
        steps.append(AgentStep("Tool Calling", "RAG 검색 이후 필요한 local tool을 선택하고 실행합니다.", tool_context))

    if verbose:
        print("\n[2] 근거 기반 초안 생성 중...")
    _notify(progress_callback, "초안 생성", "running")

    draft = ask_ai(
        """
        You are a RAG execution agent.
        Answer the user's request using only the retrieved context when factual grounding is needed.
        If the retrieved context is insufficient, say what is missing instead of inventing facts.
        Write Markdown normally. Do not escape Markdown characters such as *, #, [, or ].
        """,
        f"""
        User request:
        {task}

        Task analysis:
        {analysis}

        Retrieved context:
        {context or "No matching local documents were found."}

        Tool results:
        {tool_context or "Tool calls disabled."}
        """,
        client=client,
    )
    draft = normalize_markdown_escapes(draft)
    state.draft = draft
    steps.append(AgentStep("초안 생성", "검색된 문서 근거를 바탕으로 초안을 작성합니다.", draft))
    _notify(progress_callback, "초안 생성", "complete")

    if verbose:
        print("\n[3] 근거 및 품질 검토 중...")
    _notify(progress_callback, "품질 검토", "running")

    final_result = ask_ai(
        """
        You are a quality review agent for a RAG answer.
        Review the draft for clarity, completeness, and faithfulness to the retrieved context.
        Return only the improved final answer.
        Do not include a sources section; citations will be appended separately.
        Write Markdown normally. Do not escape Markdown characters such as *, #, [, or ].
        """,
        f"""
        Original request:
        {task}

        Retrieved context:
        {context or "No matching local documents were found."}

        Tool results:
        {tool_context or "Tool calls disabled."}

        Draft:
        {draft}
        """,
        client=client,
    )
    final_result = normalize_markdown_escapes(final_result)
    final_with_citations = f"{final_result}\n\n---\n{citations}"
    state.review = final_result
    state.final_answer = final_with_citations
    steps.append(AgentStep("품질 검토", "초안의 정확성, 충실성, 출처 표시를 검토합니다.", final_with_citations))
    _notify(progress_callback, "품질 검토", "complete")

    result = AgentRunResult(task=task, steps=steps, final_answer=final_with_citations, state=state)
    if include_steps:
        return result

    return result.final_answer


if __name__ == "__main__":
    print("=== IYUNO Agent Portfolio ===")

    user_task = input("\n처리할 작업을 입력하세요: ")

    result = run_agent(user_task)

    print("\n=== 최종 결과 ===")
    print(result)
