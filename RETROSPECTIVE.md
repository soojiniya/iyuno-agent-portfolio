# 프로젝트 회고

## 1. 프로젝트 목표

이 프로젝트의 목표는 IYUNO AI Agent Engineer 채용공고의 요구 역량을 분석하고, 이를 실제로 동작하는 AI Agent 프로젝트로 구현하여 GitHub 포트폴리오로 증명하는 것이었다. 단순히 OpenAI API를 한 번 호출하는 챗봇이 아니라, 사용자 요청을 분석하고 필요한 정보를 검색하거나 도구를 사용한 뒤, 초안 생성과 품질 검토를 거쳐 최종 답변을 만드는 multi-step agent workflow를 구현하는 데 중점을 두었다.

## 2. 구현한 내용

- OpenAI API 기반 AI Agent: Local Live Mode에서 실제 OpenAI API를 사용해 사용자 입력에 따른 응답을 생성할 수 있도록 구성했다.
- Multi-step Workflow: `Analyze → Retrieve → Use Tools → Draft → Review → Final` 흐름을 지원하되, RAG 검색과 Tool 사용은 사용자가 선택할 수 있는 optional 단계로 구현했다.
- RAG 문서 검색 및 Citation: `data/iyuno_ai_agent_notes.md` 문서를 로드하고, chunking, embedding, vector similarity search를 거쳐 관련 문서를 검색한 뒤 citation을 표시한다.
- Local Tool Calling: 외부 유료 API가 아니라 local Python function 기반으로 `calculator`, `date_diff`, `text_stats` 도구를 구현했다.
- AgentState 기반 상태 관리: `original_request`, `analysis`, `retrieved_context`, `tool_results`, `draft`, `review`, `final_answer`, `citations`를 한 번의 Agent 실행 안에서 관리한다.
- Streamlit UI: Demo Mode / Live Mode, RAG 사용 여부, Tool Calling 사용 여부, 단계별 결과, 최종 답변, 피드백 입력을 확인할 수 있는 웹 UI를 만들었다.
- SQLite 사용자 피드백 저장: 사용자가 남긴 도움 여부와 코멘트를 SQLite DB에 저장하는 feedback loop를 추가했다.
- Evaluation: 32개 evaluation case를 구성하고 deterministic local evaluator로 평가 결과를 생성했다.
- 테스트 및 CI: 30개의 단위 테스트를 구성하고 pytest로 전체 테스트를 검증했으며, GitHub Actions CI에서 compile check, pytest, deterministic evaluation을 자동 실행하도록 구성했다.
- 평가 산출물: `evaluation/metrics.json`과 `evaluation/evaluation_results.png`를 생성하여 평가 결과를 문서화했다.
- Public Demo Mode와 Local Live Mode: 공개 Streamlit 배포에서는 API 비용 보호를 위해 Demo Mode를 사용하고, 로컬 환경에서는 API key 설정 후 Live Mode로 실제 OpenAI API를 사용할 수 있도록 분리했다.

## 3. 주요 평가 결과

`evaluation/metrics.json` 기준 실제 평가 결과는 다음과 같다.

| Metric | Result |
| --- | ---: |
| Total cases | 32 |
| Passed cases | 32 |
| Task Success | 100.00% |
| Keyword Accuracy | 100.00% |
| Recall@k | 100.00% |
| Citation Rate | 100.00% |
| Faithfulness Proxy | 75.00% |
| Average Latency | 0.000329s |
| Estimated Total Tokens | 7,578 |
| Estimated Cost | $0.00075780 |

이 평가는 실제 OpenAI Live API benchmark가 아니라 deterministic local evaluation 기준이다. Faithfulness Proxy는 외부 LLM judge가 아닌 간단한 deterministic proxy metric이므로, 향후 더 정교한 평가 지표로 개선할 여지가 있다.

## 4. 한계

- RAG 데이터가 현재 제한된 샘플 문서 중심이기 때문에 다양한 도메인의 질문을 충분히 검증하기에는 부족하다.
- Tool Calling은 `calculator`, `date_diff`, `text_stats` 같은 local Python tool 중심이며, 실제 외부 서비스 API orchestration까지 확장된 구조는 아니다.
- Evaluation은 32개 고정 케이스 중심이므로 실제 사용자 입력의 다양성을 모두 반영하기에는 한계가 있다.
- 공개 Streamlit 환경에서는 API 비용과 보안 문제로 Demo Mode만 제공한다.
- SQLite 피드백 저장은 구현했지만, 실제 서비스 수준의 외부 DB, 인증, 운영 모니터링 연동은 제한적이다.

## 5. 향후 개선 방향

- RAG 데이터 확장: 공개 문서와 도메인 데이터를 추가하여 검색 범위와 답변 다양성을 높인다.
- 외부 API 연동: Web/API/DB 등 외부 서비스와 연결하여 실제 업무 자동화에 가까운 Tool Calling으로 확장한다.
- 평가 데이터셋 및 지표 확대: 더 다양한 질문 유형, 실패 케이스, LLM-as-a-judge 또는 human review 기반 평가를 추가한다.
- 피드백 활용 고도화: SQLite에 축적된 사용자 피드백을 분석하여 프롬프트, 검색 품질, 도구 선택 로직 개선에 활용한다.

## 6. 프로젝트를 통해 배운 점

이번 프로젝트를 통해 단순 LLM 호출과 Agent 시스템 설계의 차이를 체감했다. Agent는 답변 생성 자체보다도 요청 분석, 컨텍스트 검색, 도구 사용, 상태 관리, 검토, 평가가 하나의 흐름으로 연결되어야 안정적으로 동작한다는 점이 중요했다. 또한 RAG, Tool Calling, State Management를 따로 구현하는 것보다 이 결과들이 draft와 review 단계의 context로 자연스럽게 전달되도록 설계하는 과정이 핵심이었다.

마지막으로 Evaluation, 테스트, CI를 함께 구성하면서 기능 구현만큼 검증과 재현성이 중요하다는 것을 배웠다. GitHub README, metrics, chart, CI badge, 회고 문서까지 정리하면서 구현 결과를 단순 코드가 아니라 제출 가능한 증거로 문서화하는 과정의 중요성도 확인했다.
