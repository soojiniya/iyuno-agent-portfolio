# IYUNO AI Agent Portfolio

AI Agent Engineer 포트폴리오를 위해 만든 multi-step AI Agent workflow 프로젝트입니다.

단순히 OpenAI API를 한 번 호출하는 챗봇이 아니라, 하나의 사용자 요청을 여러 Agent 단계로 나누어 처리하고 최종 결과를 개선하는 구조를 보여주는 것이 목표입니다.

## Workflow

```text
사용자 요청
→ 1. 요청 분석
→ 2. 초안 생성
→ 3. 품질 검토
→ 최종 결과
```

각 단계는 OpenAI Responses API를 호출하며, 이전 단계의 결과를 다음 단계의 입력으로 전달합니다.

## 주요 기능

- OpenAI API 기반 LLM 호출
- 분석 / 초안 생성 / 품질 검토로 분리된 Agent workflow
- Streamlit 웹 UI
- API 크레딧을 사용하지 않는 기본 데모 모드
- 웹 화면에서 현재 실행 중인 Agent 단계 표시
- 최종 결과와 단계별 중간 결과 확인
- Markdown 출력 정규화
- API Key 누락, 패키지 누락 등 기본 예외 처리
- API 호출 없이 실행 가능한 단위 테스트
- `evaluation/` 기반의 간단한 Agent 결과 평가 구조

## 프로젝트 구조

```text
.
├── src/
│   ├── app.py              # OpenAI API 호출 및 Agent workflow
│   └── web_app.py          # Streamlit 웹 UI
├── tests/
│   └── test_app.py         # Markdown 정규화 및 workflow 단위 테스트
├── evaluation/
│   ├── sample_cases.json   # 평가용 샘플 태스크
│   └── evaluate_agent.py   # 간단한 키워드 기반 평가 실행 스크립트
├── data/                   # 향후 문서/RAG 데이터 저장 위치
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 설치 방법

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`.env.example`을 참고해 `.env` 파일을 생성합니다.

```text
OPENAI_API_KEY=your_openai_api_key_here
```

필요하면 사용할 모델을 지정할 수 있습니다.

```text
OPENAI_MODEL=gpt-5.6
```

## 실행 방법

CLI 실행:

```bash
python src/app.py
```

Streamlit 실행:

```bash
streamlit run src/web_app.py
```

웹 앱은 기본적으로 데모 모드로 실행됩니다. 실제 OpenAI API를 사용하려면 사이드바에서 `데모 모드 (API 사용 안 함)`을 해제하세요.

공개 배포 환경에서는 API 크레딧 보호를 위해 Live Mode를 비활성화할 수 있습니다.

```text
IYUNO_PUBLIC_DEMO_ONLY=true
```

이 값이 설정되었거나 Streamlit Community Cloud 환경이 감지되면 웹 앱은 데모 모드만 사용하며 실제 OpenAI API를 호출하지 않습니다.

## 테스트

```bash
python -m unittest discover -s tests
```

테스트는 실제 OpenAI API를 호출하지 않고 fake client를 사용합니다.

## Evaluation

샘플 평가 실행:

```bash
python evaluation/evaluate_agent.py
```

현재 평가는 `sample_cases.json`의 필수 키워드 포함 여부를 기준으로 점수를 계산합니다. 향후에는 다음과 같이 확장할 수 있습니다.

- LLM-as-a-judge 기반 품질 평가
- 정확성, 완성도, 톤, 형식 준수 여부 평가
- 실패 케이스 분석 리포트 생성
- RAG 또는 tool calling 결과의 citation 검증

## Markdown 출력 문제 해결

일부 모델 응답에서 다음처럼 Markdown 문자가 escape되어 반환될 수 있습니다.

```text
\*\*[현재 배송 위치]\*\*
```

Streamlit에서만 임시로 문자열을 치환하면 CLI, 테스트, 평가 결과에는 같은 문제가 남습니다. 그래서 `src/app.py`의 `normalize_markdown_escapes()`에서 Agent 최종 출력과 단계별 출력을 공통으로 정규화합니다.

## 보안

- `.env`는 `.gitignore`에 포함되어 있어 GitHub에 올라가지 않도록 설정되어 있습니다.
- 실제 API Key는 `.env.example`이 아니라 로컬 `.env`에만 저장해야 합니다.
- 공개 배포 시에는 `IYUNO_PUBLIC_DEMO_ONLY=true`를 설정해 Live Mode를 비활성화하는 것을 권장합니다.
- 커밋 전 `git status --ignored`로 `.env`가 ignored 상태인지 확인하는 것을 권장합니다.

## 향후 개선 방향

- Agent 단계별 prompt 품질 개선
- 평가 케이스 확대
- LLM-as-a-judge 평가 추가
- RAG 기반 문서 검색 기능 추가
- Tool calling 예제 추가
- Streamlit UI에서 실행 이력 저장
