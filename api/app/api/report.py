import platform
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import require_app_password
from app.db import get_session
from app.services.analytics import report_context

router = APIRouter(tags=["report"], dependencies=[Depends(require_app_password)])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


@router.get("/report", response_class=HTMLResponse)
def get_report(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    context = report_context(session)
    return templates.TemplateResponse(name="report.html", context={"request": request, **context})


@router.get("/report.pdf")
def get_report_pdf(request: Request, session: Session = Depends(get_session)) -> Response:
    context = report_context(session)
    html = templates.get_template("report.html").render(**context)

    try:
        if platform.system().lower() != "windows":
            from weasyprint import HTML

            pdf = HTML(string=html, base_url=str(request.base_url)).write_pdf()
        else:
            raise RuntimeError("WeasyPrint disabled on Windows runtime")
    except Exception:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except Exception as exc:
            raise HTTPException(status_code=501, detail="No PDF engine available") from exc

        buffer = BytesIO()
        pdf_canvas = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 50

        lines = [
            "Friction Finder COO Report",
            f"Generated: {context['generated']}",
            f"Total pain points: {context['kpis']['total_pain_points']}",
            f"Total hours/week: {context['kpis']['total_hours_per_week']}",
            "Top backlog:",
        ]
        for item in context["top_backlog"][:10]:
            lines.append(
                f"- {item['title']} | team={item['team']} | priority={item['priority_score']} | impact={item['impact_hours_per_week']}h/w"
            )

        for line in lines:
            if y < 50:
                pdf_canvas.showPage()
                y = height - 50
            pdf_canvas.drawString(40, y, line[:120])
            y -= 18

        pdf_canvas.save()
        pdf = buffer.getvalue()
        buffer.close()

    headers = {"Content-Disposition": "attachment; filename=friction-finder-report.pdf"}
    return Response(content=pdf, media_type="application/pdf", headers=headers)
