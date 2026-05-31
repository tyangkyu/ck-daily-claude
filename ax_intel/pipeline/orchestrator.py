from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from ax_intel.cleaning.pipeline import clean_items
from ax_intel.distribution.slack_message import render_slack_message
from ax_intel.distribution.slack_upload import upload_slack
from ax_intel.insights.writer import generate_phase6_outputs
from ax_intel.io import read_json, write_json
from ax_intel.models import (
    CleanItem,
    HeroStory,
    Insight,
    PipelineStepResult,
    RawItem,
    RunContext,
    RunLog,
    RunMode,
    Signal,
)
from ax_intel.reporting.exporters import write_docx, write_pdf
from ax_intel.reporting.renderer import (
    build_manifest,
    render_archive_markdown,
    render_email_html,
    render_report_markdown,
)
from ax_intel.scoring.ranker import score_items
from ax_intel.source_clients.rss import collect_rss_feed
from ax_intel.config import load_config
from ax_intel.validation.engine import run_validation
from ax_intel.visuals.placeholder_png import write_solid_png
from ax_intel.visuals.prompt import build_hero_prompt


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _record_step(name: str, fn: Callable[[], Tuple[List[Path], str]]) -> PipelineStepResult:
    started_at = _now()
    try:
        output_paths, message = fn()
        status = "completed"
    except Exception as exc:
        output_paths = []
        message = str(exc)
        status = "failed"
    finished_at = _now()
    return PipelineStepResult(
        name=name,
        status=status,
        output_paths=output_paths,
        message=message,
        started_at=started_at,
        finished_at=finished_at,
    )


def collect_step(context: RunContext) -> Tuple[List[Path], str]:
    from datetime import timedelta

    sources_config = load_config("sources.yaml")
    discovered_at = context.created_at
    cutoff_at = discovered_at - timedelta(hours=context.collection_window_hours)
    collected: List[RawItem] = []
    errors: List[str] = []
    for feed in sources_config.get("rss_feeds", []):
        if context.dry_run and not feed.get("offline_only", False):
            continue
        if not context.dry_run and feed.get("offline_only", False):
            continue
        try:
            collected.extend(
                collect_rss_feed(
                    feed_url=feed["url"],
                    source_name=feed["name"],
                    source_tier=feed["tier"],
                    default_companies=feed.get("companies", []),
                    default_scope=feed.get("scope", []),
                    discovered_at=discovered_at,
                    cutoff_at=cutoff_at,
                )
            )
        except Exception as exc:
            errors.append(f"{feed['name']}: {exc}")
    if not collected:
        raise RuntimeError(f"No items collected. Feed errors: {errors}")
    write_json(context.output_paths["raw_items"], [item.model_dump(mode="json") for item in collected])
    msg = f"Collected {len(collected)} raw items"
    if errors:
        msg += f" ({len(errors)} feeds skipped)"
    return [context.output_paths["raw_items"]], msg


def clean_step(context: RunContext) -> Tuple[List[Path], str]:
    raw_items = [RawItem.model_validate(item) for item in read_json(context.output_paths["raw_items"])]
    cleaned = clean_items(raw_items)
    write_json(context.output_paths["clean_items"], [item.model_dump(mode="json") for item in cleaned])
    return [context.output_paths["clean_items"]], f"Cleaned {len(cleaned)} items"


def score_step(context: RunContext) -> Tuple[List[Path], str]:
    cleaned = [CleanItem.model_validate(item) for item in read_json(context.output_paths["clean_items"])]
    signals = score_items(cleaned)
    write_json(context.output_paths["signals"], [signal.model_dump(mode="json") for signal in signals])
    return [context.output_paths["signals"]], f"Scored {len(signals)} signals"


def insights_step(context: RunContext) -> Tuple[List[Path], str]:
    cleaned = [CleanItem.model_validate(item) for item in read_json(context.output_paths["clean_items"])]
    signals = [Signal.model_validate(signal) for signal in read_json(context.output_paths["signals"])]
    insights, hero_story = generate_phase6_outputs(signals, cleaned)
    write_json(context.output_paths["insights"], [insight.model_dump(mode="json") for insight in insights])
    write_json(context.output_paths["hero_story"], hero_story.model_dump(mode="json"))
    return [context.output_paths["insights"], context.output_paths["hero_story"]], f"Generated {len(insights)} insights"


def hero_visual_step(context: RunContext) -> Tuple[List[Path], str]:
    hero_story = HeroStory.model_validate(read_json(context.output_paths["hero_story"]))
    signals = [Signal.model_validate(signal) for signal in read_json(context.output_paths["signals"])]
    prompt = build_hero_prompt(hero_story, signals, context.run_date)
    context.output_paths["hero_prompt"].write_text(prompt, encoding="utf-8")
    write_solid_png(context.output_paths["hero_image"], size=(1600, 900))
    return [context.output_paths["hero_prompt"], context.output_paths["hero_image"]], "Generated hero prompt and placeholder image"


def report_step(context: RunContext) -> Tuple[List[Path], str]:
    signals = [Signal.model_validate(signal) for signal in read_json(context.output_paths["signals"])]
    insights = [Insight.model_validate(insight) for insight in read_json(context.output_paths["insights"])]
    hero_story = HeroStory.model_validate(read_json(context.output_paths["hero_story"]))
    report_markdown = render_report_markdown(context=context, signals=signals, insights=insights, hero_story=hero_story)
    email_html = render_email_html(context=context, signals=signals, insights=insights, hero_story=hero_story)
    archive_markdown = render_archive_markdown(context=context, signals=signals, insights=insights, hero_story=hero_story)
    manifest = build_manifest(context)
    context.output_paths["report_markdown"].write_text(report_markdown, encoding="utf-8")
    context.output_paths["email_html"].write_text(email_html, encoding="utf-8")
    context.output_paths["archive_markdown"].write_text(archive_markdown, encoding="utf-8")
    write_docx(context.output_paths["report_docx"], report_markdown)
    write_pdf(context.output_paths["report_pdf"], report_markdown)
    write_json(context.output_paths["report_manifest"], manifest.model_dump(mode="json"))
    return [
        context.output_paths["report_markdown"],
        context.output_paths["report_docx"],
        context.output_paths["report_pdf"],
        context.output_paths["email_html"],
        context.output_paths["archive_markdown"],
        context.output_paths["report_manifest"],
    ], "Rendered report artifacts"


def slack_message_step(context: RunContext) -> Tuple[List[Path], str]:
    signals = [Signal.model_validate(signal) for signal in read_json(context.output_paths["signals"])]
    clean_items = [CleanItem.model_validate(item) for item in read_json(context.output_paths["clean_items"])]
    insights = [Insight.model_validate(insight) for insight in read_json(context.output_paths["insights"])]
    hero_story = HeroStory.model_validate(read_json(context.output_paths["hero_story"]))
    manifest = build_manifest(context)
    message = render_slack_message(
        context=context,
        signals=signals,
        insights=insights,
        hero_story=hero_story,
        manifest=manifest,
        clean_items=clean_items,
    )
    context.output_paths["slack_message"].write_text(message, encoding="utf-8")
    return [context.output_paths["slack_message"]], "Rendered Slack message artifact"


def slack_upload_step(context: RunContext) -> Tuple[List[Path], str]:
    result = upload_slack(context)
    write_json(context.output_paths["slack_send_result"], result.model_dump(mode="json"))
    return [context.output_paths["slack_send_result"]], result.status


def validation_step(context: RunContext) -> Tuple[List[Path], str]:
    validation = run_validation(context)
    write_json(context.output_paths["validation_result"], validation.model_dump(mode="json"))
    return [context.output_paths["validation_result"]], "passed" if validation.passed else "failed"


def run_pipeline(
    *,
    context: RunContext,
    mode: RunMode,
    approval_token: Optional[str] = None,  # noqa: ARG001 — retained for API compatibility
) -> RunLog:
    pipeline_started_at = _now()
    context.report_dir.mkdir(parents=True, exist_ok=True)
    write_json(context.output_paths["run_context"], context.model_dump(mode="json"))

    steps: List[PipelineStepResult] = [
        PipelineStepResult(
            name="init_run",
            status="completed",
            output_paths=[context.output_paths["run_context"]],
            message="Initialized run context",
            started_at=pipeline_started_at,
            finished_at=_now(),
        )
    ]
    planned_steps = [
        ("collect_sources", lambda: collect_step(context)),
        ("clean_and_rank_sources", lambda: clean_step(context)),
        ("score_signals", lambda: score_step(context)),
        ("generate_insights", lambda: insights_step(context)),
        ("generate_hero_visual", lambda: hero_visual_step(context)),
        ("render_report", lambda: report_step(context)),
        ("render_slack_message", lambda: slack_message_step(context)),
        ("send_slack", lambda: slack_upload_step(context)),
        ("validate_outputs", lambda: validation_step(context)),
    ]
    for name, fn in planned_steps:
        step = _record_step(name, fn)
        steps.append(step)
        if step.status != "completed":
            break

    validation_passed = False
    if steps and steps[-1].name == "validate_outputs" and steps[-1].status == "completed":
        validation_passed = steps[-1].message == "passed"
    status = "completed" if validation_passed else "failed"
    run_log = RunLog(
        run_date=context.run_date,
        status=status,
        mode=mode,
        dry_run=context.dry_run,
        report_dir=context.report_dir,
        steps=steps,
        validation_passed=validation_passed,
        started_at=pipeline_started_at,
        finished_at=_now(),
    )
    write_json(context.output_paths["run_log"], run_log.model_dump(mode="json"))
    return run_log
