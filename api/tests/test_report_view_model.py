from app.api.report import _build_report_view_model


def test_report_view_model_uses_selected_hourly_rate_and_currency() -> None:
    context = {
        "kpis": {
            "total_pain_points": 2,
            "total_hours_per_week": 10.0,
            "top_categories": [{"category": "client_ops", "count": 2}],
        },
        "top_backlog": [],
        "team_breakdown": [],
        "category_breakdown": [],
        "estimated_hours_saved": 4.0,
    }

    view = _build_report_view_model(
        context=context,
        hourly_rate=40.0,
        currency="GBP",
        quick_win_threshold=5.0,
    )

    assert view["currency_code"] == "GBP"
    assert view["roi_annual_hours"] == "520.0"
    assert view["roi_weekly_cost"] == "£400"
    assert view["roi_annual_cost"] == "£20,800"
