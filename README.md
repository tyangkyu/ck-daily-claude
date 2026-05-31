# ck-daily

PR #1 implements the Phase 0~2 foundation from `blueprint-ax-commerce-intelligence.md`.
PR #2 adds the Phase 3 RSS collection skeleton.
PR #3 adds the Phase 4 cleaning and duplicate removal skeleton.
PR #4 adds the Phase 5 deterministic scoring skeleton.
PR #5 adds the Phase 6 deterministic insight and hero story skeleton.
PR #6 adds the Phase 7 hero visual prompt and placeholder image skeleton.
PR #7 adds the Phase 8 markdown, email HTML, and archive report skeleton.
PR #8 adds the Phase 8 DOCX/PDF export skeleton.
PR #9 adds the Phase 9 Gmail draft skeleton.
PR #10 adds the Phase 10 validation engine skeleton.
PR #11 adds the Phase 11 end-to-end daily pipeline skeleton.
PR #12 adds a Slack-ready message artifact for the ck-daily PoC.
PR #13 adds Slack upload/send-result plumbing for PoC distribution.

## Scope

- Repository skeleton
- Configuration files
- Pydantic data models
- `init_run.py` CLI
- Pytest coverage for the initial JSON contracts
- RSS collector skeleton
- `collect_sources.py` CLI
- Local fixture feeds for deterministic execution
- URL canonicalization and duplicate removal
- `clean_and_rank_sources.py` CLI
- Deterministic scoring and priority mapping
- `score_signals.py` CLI
- Deterministic executive insight generation
- `generate_insights.py` CLI
- [뉴스레터체] hero visual prompt generation
- `generate_hero_visual.py` CLI
- Markdown report, HTML email, archive, and manifest generation
- Minimal DOCX/PDF export
- `render_report.py` CLI
- Gmail draft preview and send-result skeleton
- `send_gmail.py` CLI
- Output validation engine
- `validate_outputs.py` CLI
- End-to-end pipeline orchestration
- `daily_pipeline.py` CLI
- Slack-ready message generation
- `render_slack_message.py` CLI
- Slack dry-run/live upload skeleton
- `send_slack.py` CLI

Later phases will add real Gmail API integration and production scheduling.

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 scripts/init_run.py --date 2026-05-31 --dry-run
python3 scripts/collect_sources.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/clean_and_rank_sources.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/score_signals.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/generate_insights.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/generate_hero_visual.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/render_report.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/render_slack_message.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/send_slack.py --run-context Reports/2026-05-31/run-context.json
python3 scripts/validate_outputs.py --run-context Reports/2026-05-31/run-context.json
pytest
```

Or run the current end-to-end skeleton:

```bash
python3 scripts/daily_pipeline.py --date 2026-05-31 --dry-run
```

`send_gmail.py` is draft-only by default. `--mode send` is currently a guarded stub and requires `--approval-token`.
`send_slack.py` is dry-run safe by default. Live Slack posting requires `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_ID`.
