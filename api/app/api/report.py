import json
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
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

router = APIRouter(tags=["report"], dependencies=[Depends(require_app_password)])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
REPORT_CSS_PATH = TEMPLATE_DIR / "report.css"
ASSUMED_HOURLY_RATE_USD = 85.0


@router.get("/report", response_class=HTMLResponse)
def get_report(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    context = _build_report_view_model(report_context(session))
    return templates.TemplateResponse(name="report.html", context={"request": request, **context})


@router.get("/report.pdf")
def get_report_pdf(request: Request, session: Session = Depends(get_session)) -> Response:
    context = _build_report_view_model(report_context(session))
    html = templates.get_template("report.html").render(**context)

    try:
        from weasyprint import HTML

        pdf = HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
    except Exception:
        pdf = _build_reportlab_pdf(context)

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


def _fmt_currency(value: Any) -> str:
    return f"${_fmt_number(_safe_float(value), 0)}"


def _priority_band(priority: float) -> str:
    if priority >= 12:
        return "high"
    if priority >= 6:
        return "medium"
    return "low"


def _build_report_view_model(context: dict[str, Any]) -> dict[str, Any]:
    kpis = context.get("kpis", {})
    top_backlog = list(context.get("top_backlog", []))
    team_breakdown = list(context.get("team_breakdown", []))

    total_hours_week = _safe_float(kpis.get("total_hours_per_week", 0.0))
    annual_cost = total_hours_week * ASSUMED_HOURLY_RATE_USD * 52
    annual_savings = _safe_float(context.get("estimated_hours_saved", 0.0)) * ASSUMED_HOURLY_RATE_USD * 52

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
    medium_impact = [item for item in ranked_backlog if 3 <= _safe_int(item.get("effort_score")) <= 3]
    strategic = [item for item in ranked_backlog if _safe_int(item.get("effort_score")) >= 4]

    max_team_total = max((_safe_int(row.get("total", 0)) for row in team_breakdown), default=1)
    team_rows: list[dict[str, Any]] = []
    for row in team_breakdown:
        total = _safe_int(row.get("total", 0))
        width = (total / max_team_total * 100) if max_team_total else 0
        team_rows.append(
            {
                **row,
                "total_fmt": str(total),
                "bar_width_pct": _fmt_number(width, 0),
            }
        )

    css_text = ""
    if REPORT_CSS_PATH.exists():
        css_text = REPORT_CSS_PATH.read_text(encoding="utf-8")

    return {
        **context,
        "report_css": css_text,
        "assumed_hourly_rate_usd": ASSUMED_HOURLY_RATE_USD,
        "kpi_total_pain_points": str(_safe_int(kpis.get("total_pain_points", 0))),
        "kpi_total_hours_week": _fmt_hours(total_hours_week),
        "kpi_annual_cost": _fmt_currency(annual_cost),
        "kpi_annual_savings": _fmt_currency(annual_savings),
        "kpi_top_impact_area": top_impact_area,
        "ranked_backlog": ranked_backlog[:10],
        "team_rows": team_rows[:12],
        "roadmap_quick_wins": quick_wins[:5],
        "roadmap_medium_impact": medium_impact[:5],
        "roadmap_strategic": strategic[:5],
    }


def _build_reportlab_pdf(context: dict[str, Any]) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:
        raise HTTPException(status_code=501, detail="No PDF engine available") from exc

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="Friction Finder COO Report",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#102132"),
        spaceAfter=8,
    )
    h2_style = ParagraphStyle(
        "H2Style",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#173a56"),
        spaceAfter=6,
        spaceBefore=10,
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
    )
    small_style = ParagraphStyle(
        "SmallStyle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#4a5968"),
    )

    story: list[Any] = []
    story.append(Paragraph("Friction Finder COO Report", title_style))
    story.append(Paragraph(f"Generated: {context.get('generated', '-')}", small_style))
    story.append(Spacer(1, 10))

    kpis = context.get("kpis", {})
    kpi_rows = [
        ["Pain Points", str(kpis.get("total_pain_points", 0)), "Hours Lost / Week", str(kpis.get("total_hours_per_week", 0.0))],
        ["Quick Wins", str(len(kpis.get("quick_wins", []))), "Top Backlog", str(len(context.get("top_backlog", [])))],
    ]
    kpi_table = Table(kpi_rows, colWidths=[1.7 * inch, 1.2 * inch, 1.7 * inch, 1.2 * inch])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f7fb")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#102132")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d2dce6")),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(kpi_table)

    story.append(Paragraph("Executive Summary: Top Quick Wins", h2_style))
    quick_wins = context.get("executive_quick_wins", [])
    if quick_wins:
        for idx, item in enumerate(quick_wins, 1):
            text = (
                f"<b>{idx}. {item.get('title', '-')}</b><br/>"
                f"Team: {item.get('team', '-')}, Impact: {item.get('impact_hours_per_week', 0)} h/week, "
                f"Priority: {item.get('priority_score', 0)}"
            )
            story.append(Paragraph(text, body_style))
            story.append(Spacer(1, 5))
    else:
        story.append(Paragraph("No quick wins currently meet threshold.", body_style))

    story.append(Paragraph("Top 10 Ranked Automation Backlog", h2_style))
    backlog = context.get("top_backlog", [])
    if backlog:
        backlog_rows: list[list[str]] = [["#", "Pain Point", "Team", "Category", "Impact", "Effort", "Conf.", "Priority"]]
        for idx, item in enumerate(backlog[:10], 1):
            backlog_rows.append(
                [
                    str(idx),
                    str(item.get("title", "-"))[:55],
                    str(item.get("team", "-")),
                    str(item.get("category", "-")),
                    str(item.get("impact_hours_per_week", "-")),
                    str(item.get("effort_score", "-")),
                    str(item.get("confidence_score", "-")),
                    str(item.get("priority_score", "-")),
                ]
            )
        backlog_table = Table(
            backlog_rows,
            colWidths=[0.3 * inch, 2.5 * inch, 1.0 * inch, 0.8 * inch, 0.65 * inch, 0.5 * inch, 0.55 * inch, 0.7 * inch],
            repeatRows=1,
        )
        backlog_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f466f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d2dce6")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fbff")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(backlog_table)
    else:
        story.append(Paragraph("No backlog items available.", body_style))

    story.append(Paragraph("Team and Category Breakdown", h2_style))
    team_breakdown = context.get("team_breakdown", [])
    category_breakdown = context.get("category_breakdown", [])
    summary_rows = [["Type", "Name", "Count"]]
    summary_rows.extend([["Team", str(t.get("team", "-")), str(t.get("total", 0))] for t in team_breakdown[:8]])
    summary_rows.extend([["Category", str(c.get("category", "-")), str(c.get("count", 0))] for c in category_breakdown[:8]])
    summary_table = Table(summary_rows, colWidths=[0.9 * inch, 3.8 * inch, 1.0 * inch], repeatRows=1)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f1f8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d2dce6")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (2, 1), (2, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafcff")]),
            ]
        )
    )
    story.append(summary_table)

    story.append(Paragraph("Systems Involved Map", h2_style))
    systems = context.get("systems_map", [])
    if systems:
        systems_text = ", ".join([f"{s.get('system', '-')}: {s.get('mentions', 0)}" for s in systems[:12]])
        story.append(Paragraph(systems_text, body_style))
    else:
        story.append(Paragraph("No systems identified yet.", body_style))

    quotes = context.get("quotes", [])
    if quotes:
        story.append(Paragraph("Appendix: Anonymised Quotes", h2_style))
        for quote in quotes[:12]:
            quote_text = f"\"{quote.get('quote', '')}\"<br/><font color='#5a6b7c'>Pain Point #{quote.get('pain_point_id', '-')}, Team {quote.get('team', '-')}</font>"
            story.append(Paragraph(quote_text, small_style))
            story.append(Spacer(1, 4))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


@router.get("/report/latest", response_model=ReportRunResponse, dependencies=[Depends(require_app_password)])
def get_latest_report(session_id: str | None = None, session: Session = Depends(get_session)) -> ReportRunResponse:
    """Get the latest report run, optionally filtered by session_id."""
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
    """Attach a report generated by n8n workflow.

    Protected by n8n webhook secret. Creates a new ReportRun record.
    """
    # Stringify recommendations_json if provided
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
