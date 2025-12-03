from django.shortcuts import render, get_object_or_404
from ocr_app.models import OCRResult

def evaluate_view(request, pk):
    rec = get_object_or_404(OCRResult, pk=pk)
    # load all programs
    programs = ProgramCriteria.objects.all()
    recommendations = []
    for p in programs:
        reasons = []
        passed = True
        fields = rec.extracted or {}
        gpax = fields.get("gpax")
        if gpax is None or gpax < p.min_gpax:
            passed = False
            reasons.append(f"GPAX ต่ำกว่า {p.min_gpax}")
        if p.min_gpamath and (fields.get("gpamath") is None or fields.get("gpamath") < p.min_gpamath):
            passed = False
            reasons.append(f"GPAMATH ต่ำกว่า {p.min_gpamath}")
        if p.min_gpasci and (fields.get("gpasci") is None or fields.get("gpasci") < p.min_gpasci):
            passed = False
            reasons.append(f"GPASCI ต่ำกว่า {p.min_gpasci}")
        if p.min_gpalan and (fields.get("gpalan") is None or fields.get("gpalan") < p.min_gpalan):
            passed = False
            reasons.append(f"GPALAN ต่ำกว่า {p.min_gpalan}")
        recommendations.append({"program": p, "passed": passed, "reasons": reasons})
    return render(request, "admissions/evaluate.html", {"rec": rec, "recommendations": recommendations})
