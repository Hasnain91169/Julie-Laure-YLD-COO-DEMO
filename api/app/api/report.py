import json
import logging
from io import BytesIO
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
        logger.exception("PDF engine status: weasyprint unavailable or failed; attempting reportlab fallback")
        try:
            pdf = _build_reportlab_pdf(context)
        except Exception as fallback_exc:
            logger.exception("PDF engine status: reportlab fallback failed")
            raise HTTPException(
                status_code=500,
                detail="PDF export is currently unavailable. HTML report remains available at /report.html.",
            ) from fallback_exc

    headers = {"Content-Disposition": "attachment; filename=friction-finder-report.pdf"}
    return Response(content=pdf, media_type="application/pdf", headers=headers)


def _build_reportlab_pdf(context: dict[str, Any]) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:
        raise HTTPException(status_code=500, detail="No fallback PDF engine available") from exc

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="COO Friction Intelligence Report",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title_style",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "heading_style",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
        spaceBefore=10,
    )
    body_style = ParagraphStyle(
        "body_style",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    muted_style = ParagraphStyle(
        "muted_style",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569"),
    )

    story: list[Any] = []
    story.append(Paragraph("COO Friction Intelligence Report", title_style))
    story.append(Paragraph(f"Generated: {context.get('generated', '-')}", muted_style))
    story.append(Spacer(1, 10))

    kpi_rows = [
        ["Pain Points", context.get("kpi_total_pain_points", "0"), "Hours Lost / Week", context.get("kpi_total_hours_week", "0 h")],
        ["Annual Cost", context.get("kpi_annual_cost", "-"), "Top Impact Area", context.get("kpi_top_impact_area", "None")],
    ]
    kpi_table = Table(kpi_rows, colWidths=[1.4 * inch, 1.6 * inch, 1.4 * inch, 2.2 * inch])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dbe3ea")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(kpi_table)

    story.append(Paragraph("Top Automation Opportunities", heading_style))
    backlog = list(context.get("ranked_backlog", []))
    if backlog:
        rows: list[list[str]] = [["Rank", "Pain Point", "Team", "Impact", "Priority", "Approach"]]
        for item in backlog[:10]:
            rows.append(
                [
                    str(item.get("rank", "")),
                    str(item.get("title", "-"))[:50],
                    str(item.get("team", "-")),
                    str(item.get("impact_hours_fmt", "-")),
                    str(item.get("priority_score_fmt", "-")),
                    str(item.get("automation_type", "-")),
                ]
            )
        table = Table(rows, colWidths=[0.45 * inch, 2.45 * inch, 1.0 * inch, 0.8 * inch, 0.75 * inch, 1.2 * inch], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe3ea")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No ranked opportunities available.", body_style))

    systems = list(context.get("systems_map", []))
    story.append(Paragraph("Systems Involved", heading_style))
    if systems:
        story.append(Paragraph(", ".join([f"{s.get('system', '-')}: {s.get('mentions', 0)}" for s in systems[:12]]), body_style))
    else:
        story.append(Paragraph("No systems identified.", body_style))

    quotes = list(context.get("quotes", []))
    if quotes:
        story.append(Paragraph("Appendix: Anonymised Quotes", heading_style))
        for quote in quotes[:10]:
            story.append(Paragraph(f"\"{quote.get('quote', '')}\"", body_style))
            story.append(Paragraph(f"Pain Point #{quote.get('pain_point_id', '-')}, Team {quote.get('team', '-')}", muted_style))
            story.append(Spacer(1, 4))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


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
