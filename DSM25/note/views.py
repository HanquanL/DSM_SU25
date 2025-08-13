from __future__ import annotations
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import F
from django.db.models.expressions import Window
from django.db.models.functions import RowNumber

from core.models import NotePrediction

def _latest_note_preds():
    # Latest prediction per note
    return (
        NotePrediction.objects.select_related("Note__Patient_id")
        .annotate(
            rn=Window(
                expression=RowNumber(),
                partition_by=[F("Note")],
                order_by=[F("Predicted_at").desc(), F("id").desc()],
            )
        )
        .filter(rn=1)
    )

def triage_queue(request):
    qs = _latest_note_preds()

    spec = (request.GET.get("spec") or "").upper()
    min_conf = request.GET.get("min")
    search = request.GET.get("search")  # search content or sample_name

    if spec:
        qs = qs.filter(Predicted_specialty=spec)
    if min_conf:
        try:
            qs = qs.filter(Confidence__gte=float(min_conf))
        except ValueError:
            pass
    if search:
        s = search.strip()
        qs = qs.filter(
            Note__Sample_name__icontains=s
        ) | qs.filter(Note__Transcription__icontains=s)

    qs = qs.order_by("-Confidence", "-Predicted_at")

    page_size = int(request.GET.get("page_size") or 25)
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(request.GET.get("page"))

    ctx = {
        "page_obj": page_obj,
        "paginator": paginator,
        "spec": spec,
        "min_conf": min_conf or "",
        "search": search or "",
        "page_size": page_size,
    }
    return render(request, "note/triage_queue.html", ctx)
