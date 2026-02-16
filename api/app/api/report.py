import json
import logging
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_app_password, require_webhook_secret
from app.config import get_settings
from app.db import get_session
from app.models.report_run import ReportRun
from app.schemas.report import AttachReportRequest, ReportRunResponse
from app.services.analytics import report_context

logger = logging.getLogger(__name__)

router = APIRouter(tags=["report"], dependencies=[Depends(require_app_password)])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
REPORT_CSS_PATH = TEMPLATE_DIR / "report.css"

CURRENCY_SYMBOLS: dict[str, str] = {"GBP": "£", "USD": "$", "EUR": "€"}
DEFAULT_CURRENCY = "GBP"
DEFAULT_HOURLY_RATE = 30.0
MIN_HOURLY_RATE = 10.0
MAX_HOURLY_RATE = 300.0


def _report_query_params(
    hourly_rate: float = Query(default=DEFAULT_HOURLY_RATE, ge=MIN_HOURLY_RATE, le=MAX_HOURLY_RATE),
    currency: Literal["GBP", "USD", "EUR"] = DEFAULT_CURRENCY,
) -> tuple[float, Literal["GBP", "USD", "EUR"]]:
    return hourly_rate, currency


@router.get("/report", response_class=HTMLResponse)
@router.get("/report.html", response_class=HTMLResponse)
def get_report(
    request: Request,
    params: tuple[float, Literal["GBP", "USD", "EUR"]] = Depends(_report_query_params),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    hourly_rate, currency = params
    context = _build_report_view_model(
        report_context(session),
        hourly_rate=hourly_rate,
        currency=currency,
        quick_win_threshold=get_settings().report_quickwin_impact_threshold_hours,
    )
    return templates.TemplateResponse(name="report.html", context={"request": request, **context})


@router.get("/report.pdf")
def get_report_pdf(
    params: tuple[float, Literal["GBP", "USD", "EUR"]] = Depends(_report_query_params),
    session: Session = Depends(get_session),
) -> Response:
    hourly_rate, currency = params
    context = _build_report_view_model(
        report_context(session),
        hourly_rate=hourly_rate,
        currency=currency,
        quick_win_threshold=get_settings().report_quickwin_impact_threshold_hours,
    )
    html = templates.get_template("report.html").render(**context)

    try:
        from weasyprint import HTML  # type: ignore

        logger.info("PDF engine status: weasyprint available")
        pdf = HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
    except Exception as exc:
        logger.exception("PDF engine status: weasyprint unavailable or failed")
        raise HTTPException(
            status_code=500,
            detail="PDF export is currently unavailable. HTML report remains available at /report.html.",
        ) from exc

    headers = {"Content-Disposition": "attachment; filename=friction-finder-report.pdf"}
    return Response(content=pdf, media_type="application/pdf", headers=headers)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _fmt_number(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}"


def _fmt_hours(value: Any) -> str:
    return f"{_fmt_number(_safe_float(value), 1)} h"


def _fmt_priority(value: Any) -> str:
    return _fmt_number(_safe_float(value), 2)


def _fmt_currency(value: Any, currency: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    return f"{symbol}{_fmt_number(_safe_float(value), 0)}"


def _priority_band(priority: float) -> str:
    if priority >= 12:
        return "high"
    if priority >= 6:
        return "medium"
    return "low"


def _build_report_view_model(
    context: dict[str, Any],
    hourly_rate: float,
    currency: Literal["GBP", "USD", "EUR"],
    quick_win_threshold: float,
) -> dict[str, Any]:
    kpis = context.get("kpis", {})
    top_backlog = list(context.get("top_backlog", []))
    team_breakdown = list(context.get("team_breakdown", []))
    category_breakdown = list(context.get("category_breakdown", []))

    total_hours_week = _safe_float(kpis.get("total_hours_per_week", 0.0))
    annual_hours = total_hours_week * 52
    weekly_cost = total_hours_week * hourly_rate
    annual_cost = annual_hours * hourly_rate
    annual_savings = _safe_float(context.get("estimated_hours_saved", 0.0)) * hourly_rate * 52
    weekly_cost_low = weekly_cost * 0.8
    weekly_cost_high = weekly_cost * 1.2
    annual_cost_low = annual_cost * 0.8
    annual_cost_high = annual_cost * 1.2

    top_impact_area = "None"
    top_categories = kpis.get("top_categories", [])
    if top_categories:
        top_impact_area = str(top_categories[0].get("category", "None")).replace("_", " ").title()

    ranked_backlog: list[dict[str, Any]] = []
    for idx, item in enumerate(top_backlog, 1):
        priority = _safe_float(item.get("priority_score", 0.0))
        impact = _safe_float(item.get("impact_hours_per_week", 0.0))
        ranked_backlog.append(
            {
                **item,
                "rank": idx,
                "priority_class": _priority_band(priority),
                "priority_score_fmt": _fmt_priority(priority),
                "impact_hours_fmt": _fmt_hours(impact),
                "effort_score_fmt": str(_safe_int(item.get("effort_score", 0))),
            }
        )

    quick_wins = [item for item in ranked_backlog if _safe_int(item.get("effort_score")) <= 2]
    medium_impact = [item for item in ranked_backlog if _safe_int(item.get("effort_score")) == 3]
    strategic = [item for item in ranked_backlog if _safe_int(item.get("effort_score")) >= 4]

    max_team_total = max((_safe_int(row.get("total", 0)) for row in team_breakdown), default=1)
    team_rows: list[dict[str, Any]] = []
    for row in team_breakdown:
        total = _safe_int(row.get("total", 0))
        width = (total / max_team_total * 100) if max_team_total else 0
        team_rows.append({**row, "total_fmt": str(total), "bar_width_pct": _fmt_number(width, 0)})

    max_category_total = max((_safe_int(row.get("count", 0)) for row in category_breakdown), default=1)
    category_rows: list[dict[str, Any]] = []
    for row in category_breakdown:
        count = _safe_int(row.get("count", 0))
        width = (count / max_category_total * 100) if max_category_total else 0
        category_rows.append({**row, "count_fmt": str(count), "bar_width_pct": _fmt_number(width, 0)})

    css_text = ""
    if REPORT_CSS_PATH.exists():
        css_text = REPORT_CSS_PATH.read_text(encoding="utf-8")

    return {
        **context,
        "report_css": css_text,
        "hourly_rate": _fmt_number(hourly_rate, 0),
        "currency_code": currency,
        "currency_symbol": CURRENCY_SYMBOLS.get(currency, currency),
        "quick_win_threshold": _fmt_number(quick_win_threshold, 1),
        "kpi_total_pain_points": str(_safe_int(kpis.get("total_pain_points", 0))),
        "kpi_total_hours_week": _fmt_hours(total_hours_week),
        "kpi_annual_cost": _fmt_currency(annual_cost, currency),
        "kpi_annual_savings": _fmt_currency(annual_savings, currency),
        "kpi_top_impact_area": top_impact_area,
        "roi_weekly_cost": _fmt_currency(weekly_cost, currency),
        "roi_annual_hours": _fmt_number(annual_hours, 1),
        "roi_annual_cost": _fmt_currency(annual_cost, currency),
        "roi_weekly_range": f"{_fmt_currency(weekly_cost_low, currency)} to {_fmt_currency(weekly_cost_high, currency)}",
        "roi_annual_range": f"{_fmt_currency(annual_cost_low, currency)} to {_fmt_currency(annual_cost_high, currency)}",
        "ranked_backlog": ranked_backlog[:10],
        "team_rows": team_rows[:12],
        "category_rows": category_rows[:12],
        "roadmap_quick_wins": quick_wins[:5],
        "roadmap_medium_impact": medium_impact[:5],
        "roadmap_strategic": strategic[:5],
    }


@router.get("/report/latest", response_model=ReportRunResponse, dependencies=[Depends(require_app_password)])
def get_latest_report(session_id: str | None = None, session: Session = Depends(get_session)) -> ReportRunResponse:
    query = select(ReportRun)
    if session_id:
        query = query.where(ReportRun.session_id == session_id)
    query = query.order_by(ReportRun.created_at.desc())

    report_run = session.scalar(query)
    if not report_run:
        raise HTTPException(status_code=404, detail="No report found")

    return ReportRunResponse(
        id=report_run.id,
        created_at=report_run.created_at,
        source=report_run.source,
        interview_id=report_run.interview_id,
        session_id=report_run.session_id,
        pdf_path_or_url=report_run.pdf_path_or_url,
        summary=report_run.summary,
        recommendations_json=report_run.recommendations_json,
    )


@router.post("/report/attach", response_model=ReportRunResponse)
def attach_report(
    request: AttachReportRequest,
    session: Session = Depends(get_session),
    _: None = Depends(lambda: require_webhook_secret(get_settings().n8n_webhook_secret)),
) -> ReportRunResponse:
    recommendations_str = None
    if request.recommendations_json:
        recommendations_str = json.dumps(request.recommendations_json)

    report_run = ReportRun(
        source=request.source,
        interview_id=request.interview_id,
        session_id=request.session_id,
        pdf_path_or_url=request.pdf_path_or_url,
        summary=request.summary,
        recommendations_json=recommendations_str,
    )
    session.add(report_run)
    session.commit()
    session.refresh(report_run)

    return ReportRunResponse(
        id=report_run.id,
        created_at=report_run.created_at,
        source=report_run.source,
        interview_id=report_run.interview_id,
        session_id=report_run.session_id,
        pdf_path_or_url=report_run.pdf_path_or_url,
        summary=report_run.summary,
        recommendations_json=report_run.recommendations_json,
    )
