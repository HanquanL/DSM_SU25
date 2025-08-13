from django.shortcuts import render
from core.models import RiskScore
from django.db.models.expressions import Window
from django.db.models.functions import RowNumber
from django.db.models import F, Q
from django.core.paginator import Paginator

# Create your views here.
def _latest_scores_qs():
    """
    Return a queryset of the LATEST RiskScore per patient using a window function.
    Works on SQLite 3.25+ (ships with recent Python).
    """
    return (
        RiskScore.objects.select_related("Patient_id")
        .annotate(
            rn=Window(
                expression=RowNumber(),
                partition_by=[F("Patient_id")],
                order_by=[F("Scored_at").desc(), F("id").desc()],
            )
        )
        .filter(rn=1)
    )

def risk_queue(request):
    qs = _latest_scores_qs()

    # --- Filters from query params ---
    high = request.GET.get("high")       # "1"/"true" to show high risk only
    search = request.GET.get("search")   # name search
    min_score = request.GET.get("min")   # float filter
    order = request.GET.get("order")     # "score_desc" | "score_asc" | "time_desc" | "time_asc"

    if high and high.lower() in {"1", "true", "yes"}:
        qs = qs.filter(HighRisk=True)

    if search:
        s = search.strip()
        qs = qs.filter(
            Q(Patient_id__CustFirstName__icontains=s) |
            Q(Patient_id__CustLastName__icontains=s)
        )

    if min_score:
        try:
            qs = qs.filter(Score__gte=float(min_score))
        except ValueError:
            pass

    # Ordering
    ordering = {
        "score_desc": ("-Score",),
        "score_asc": ("Score",),
        "time_desc": ("-Scored_at",),
        "time_asc": ("Scored_at",),
    }.get(order or "score_desc", ("-Score",))
    qs = qs.order_by(*ordering)

    # Pagination
    page_size = int(request.GET.get("page_size") or 25)
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(request.GET.get("page"))

    ctx = {
        "page_obj": page_obj,
        "paginator": paginator,
        "search": search or "",
        "high": (high or ""),
        "min_score": (min_score or ""),
        "order": order or "score_desc",
        "page_size": page_size,
    }
    ctx['page_size_options'] = ['25', '50', '100']
    return render(request, "risk/risk_queue.html", ctx)