# ck-daily-claude

`ck-daily-claude`는 AI, 클라우드, 플랫폼, 디지털 커머스 뉴스를 수집해 Claude 기반 경영진용 데일리 분석 리포트를 생성하는 Python 파이프라인입니다. Anthropic API key가 없으면 오프라인 템플릿 분석으로 폴백합니다.

## 설치

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 환경변수

```bash
cp .env.example .env
```

| 이름 | 필수 | 설명 |
|---|---:|---|
| `ANTHROPIC_API_KEY` | 선택 | Claude API 기반 분석 생성에 사용 |
| `ANTHROPIC_MODEL` | 선택 | 분석 모델명. 미설정 시 코드 기본값 사용 |
| `SLACK_BOT_TOKEN` | Slack 전송 시 | Slack 메시지 및 PDF 첨부 업로드용 Bot token |
| `SLACK_CHANNEL_ID` | Slack 전송 시 | 게시 대상 Slack 채널 ID |
| `SLACK_CHANNEL_NAME` | 선택 | 사람이 읽는 채널명 기록용 |
| `RUN_MODE` | 아니오 | 기본값 `draft`; 운영 전송은 CLI의 `--mode send` 사용 |

민감 정보는 `.env` 또는 실행 환경에만 넣고 GitHub에 올리지 않습니다. API key, Slack token, OAuth secret, DB 접속 정보는 코드, README, 로그, fixture에 남기지 마세요.

## 실행

전체 파이프라인 dry-run:

```bash
python3 scripts/daily_pipeline.py --date 2026-05-31 --dry-run
```

Claude 분석과 Slack 실제 게시:

```bash
python3 scripts/daily_pipeline.py --date 2026-05-31 --mode send
```

Slack 전송 성공 기준은 메시지 게시뿐 아니라 `report.pdf` 파일 첨부 성공까지 포함합니다. `SLACK_BOT_TOKEN`이 없으면 `send` 모드는 실패합니다.

## 단계별 실행

```bash
python3 scripts/init_run.py --date 2026-05-31 --dry-run
python3 scripts/collect_sources.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/clean_and_rank_sources.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/score_signals.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/generate_insights.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/render_report.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/render_slack_message.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/send_slack.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/validate_outputs.py --run-context Reports/2026-05-31/run-context.json
```

## 테스트

```bash
pytest
```

## 보안 및 산출물 관리

- `.env`, `.venv`, `.pytest_cache`, `Reports/<date>/`, 로그, OS 임시 파일은 `.gitignore`로 제외합니다.
- `Reports/.gitkeep`만 저장소에 유지하고, 일별 보고서 산출물은 커밋하지 않습니다.
- Claude API 장애나 키 누락 시 템플릿 분석으로 폴백하지만, Slack `send` 모드는 PDF 첨부 요건을 충족하지 못하면 실패하도록 관리합니다.
