# IYUNO AI Agent

AI Agent Engineer 포트폴리오를 위해 만든 multi-step AI Agent workflow 프로젝트입니다.

단순히 OpenAI API를 한 번 호출하는 챗봇이 아니라, 하나의 사용자 요청을 분석하고 초안을 생성한 뒤 품질 검토를 거쳐 최종 결과를 개선하는 Agent workflow를 구현했습니다.

## Live Demo

https://iyuno-agent-portfolio.streamlit.app

공개된 Streamlit 사이트는 OpenAI API 크레딧 보호를 위해 Demo Mode로 실행됩니다. Demo Mode에서는 미리 정의된 mock 결과를 사용하며 실제 OpenAI API를 호출하지 않습니다.

로컬 환경에서 Live Mode를 사용하면 OpenAI API를 호출해 사용자의 입력에 따라 실제 결과를 생성할 수 있습니다.

## Agent Workflow

```text
User Request → Analyze → Draft → Review → Final Result
```

각 단계는 이전 단계의 결과를 다음 단계의 입력으로 전달하는 방식으로 구성되어 있습니다.

## Core Features

- User Request Analysis
- Draft Generation
- Quality Review
- Final Result
- Streamlit Web UI
- Demo Mode / Live Mode
- 단계별 진행 상태 표시
- 최종 결과와 Agent 단계별 중간 결과 확인
- Markdown 출력 정규화
- Local Tool Calling: calculator, date difference, text statistics
- API 호출 없이 실행 가능한 단위 테스트
- `evaluation/` 기반의 간단한 Agent 결과 평가 구조

## Tech Stack

- Python
- OpenAI API
- Streamlit
- python-dotenv
- unittest

## Project Structure

```text
.
├── src/
│   ├── app.py              # OpenAI API 호출 및 Agent workflow
│   └── web_app.py          # Streamlit 웹 UI
├── tests/
│   ├── test_app.py         # Markdown 정규화 및 workflow 단위 테스트
│   └── test_web_app.py     # Streamlit UI 모드 분기 테스트
├── evaluation/
│   ├── sample_cases.json   # 평가용 샘플 태스크
│   └── evaluate_agent.py   # 간단한 키워드 기반 평가 실행 스크립트
├── data/                   # 향후 문서/RAG 데이터 저장 위치
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`.env.example`을 참고해 로컬 `.env` 파일을 생성합니다.

```text
OPENAI_API_KEY=your_openai_api_key_here
```

필요하면 사용할 모델을 지정할 수 있습니다.

```text
OPENAI_MODEL=gpt-5.6
```

## Run Locally

CLI 실행:

```bash
python src/app.py
```

Streamlit 실행:

```bash
streamlit run src/web_app.py
```

웹 앱은 기본적으로 Demo Mode로 실행됩니다. 실제 OpenAI API를 사용하려면 로컬 환경에서 사이드바의 `데모 모드 (API 사용 안 함)`을 해제하세요.

## Demo Mode and Live Mode

- Demo Mode: OpenAI API를 호출하지 않고 mock 결과를 사용합니다.
- Live Mode: OpenAI API를 사용해 사용자 입력에 따른 실제 Agent 결과를 생성합니다.
- Public deployment: API 크레딧 보호를 위해 Demo Mode만 허용합니다.
- RAG: `data/` 폴더의 `.txt` 또는 `.md` 문서를 검색해 답변 근거와 citation을 표시합니다.

공개 배포 환경에서는 다음 환경변수로 Live Mode를 비활성화할 수 있습니다.

```text
IYUNO_PUBLIC_DEMO_ONLY=true
```

이 값이 설정되었거나 Streamlit Community Cloud 환경이 감지되면 웹 앱은 실제 OpenAI API를 호출하지 않습니다.

## RAG Usage

1. `data/` 폴더에 공개 문서(`.txt` 또는 `.md`)를 추가합니다.
2. 로컬 Streamlit 앱에서 `RAG 사용 (data 폴더 문서 검색)`을 체크합니다.
3. Demo Mode에서는 mock RAG 결과를 사용하고, Live Mode에서만 OpenAI embedding/API를 사용합니다.
4. 최종 답변 하단에 사용된 문서 source가 `filename#chunk-n` 형식으로 표시됩니다.

## Tool Calling Usage

로컬 Python 함수 기반 tool을 사용할 수 있습니다.

- Calculator: 사칙연산 및 간단한 수식 계산
- Date Difference: `YYYY-MM-DD` 형식 날짜 간 차이 계산
- Text Statistics: 단어 수, 공백 포함/제외 문자 수 계산

Streamlit 앱에서 `Tool Calling 사용 (local tools)`을 체크하면 Agent가 요청 내용을 기준으로 필요한 tool을 선택해 실행하고, tool 결과를 draft 단계 context에 포함합니다. Tool 자체는 외부 유료 API를 사용하지 않습니다.

## Test

```bash
python -m unittest discover -s tests
```

테스트는 실제 OpenAI API를 호출하지 않고 fake/mock client를 사용합니다.

## CI

GitHub Actions runs automatically on push and pull request.
The CI workflow installs dependencies, compiles Python files, runs unit tests,
and executes deterministic evaluation without requiring an OpenAI API key.

## Evaluation

샘플 평가 실행:

```bash
python evaluation/evaluate_agent.py
```

The evaluator uses `evaluation/sample_cases.json` and does not call the OpenAI API.
It writes the report to `evaluation/metrics.json`.

Main metrics:

- Task success / keyword accuracy
- Recall@k for RAG retrieval cases
- Citation rate for RAG answers
- Average latency
- Estimated token and cost metric
- Deterministic faithfulness proxy

The evaluation set includes 30+ cases across general Agent requests, RAG questions,
Tool Calling questions, and mixed RAG + Tool workflows.

현재 평가는 `sample_cases.json`의 필수 키워드 포함 여부를 기준으로 점수를 계산합니다. 향후에는 다음과 같이 확장할 수 있습니다.

- LLM-as-a-judge 기반 품질 평가
- 정확성, 완성도, 톤, 형식 준수 여부 평가
- 실패 케이스 분석 리포트 생성
- RAG 또는 tool calling 결과의 citation 검증

## Markdown Output Handling

일부 모델 응답에서 다음처럼 Markdown 문자가 escape되어 반환될 수 있습니다.

```text
\*\*[현재 배송 위치]\*\*
```

Streamlit에서만 임시로 문자열을 치환하면 CLI, 테스트, 평가 결과에는 같은 문제가 남습니다. 그래서 `src/app.py`의 `normalize_markdown_escapes()`에서 Agent 최종 출력과 단계별 출력을 공통으로 정규화합니다.

## Security

- `.env`는 `.gitignore`에 포함되어 있어 GitHub에 올라가지 않도록 설정되어 있습니다.
- 실제 API Key는 `.env.example`이 아니라 로컬 `.env`에만 저장해야 합니다.
- API Key의 실제 값은 README나 코드에 작성하지 않습니다.
- 공개 배포 시에는 `IYUNO_PUBLIC_DEMO_ONLY=true`를 설정해 Live Mode를 비활성화하는 것을 권장합니다.
- 커밋 전 `git status --ignored`로 `.env`가 ignored 상태인지 확인하는 것을 권장합니다.

## Future Improvements

- Agent 단계별 prompt 품질 개선
- 평가 케이스 확대
- LLM-as-a-judge 평가 추가
- RAG 기반 문서 검색 기능 추가
- Tool calling 예제 추가
- Streamlit UI에서 실행 이력 저장
