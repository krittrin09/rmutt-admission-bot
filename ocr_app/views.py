from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.core.files.storage import default_storage
from .models import OCRResult
from .utils.ocr import image_to_text, extract_fields_from_lines
import os

def upload_view(request):
    if request.method == "POST":
        f = request.FILES.get("file")
        if not f:
            return render(request, "upload.html", {"error":"โปรดเลือกไฟล์"})
        # save file to media
        path = default_storage.save("transcripts/" + f.name, f)
        fullpath = os.path.join(settings.MEDIA_ROOT, path)
        # run tesseract
        lines = image_to_text(fullpath)
        fields = extract_fields_from_lines(lines)
        rec = OCRResult.objects.create(image=path, raw_text="\n".join(lines), extracted=fields)
        return redirect("ocr_result", pk=rec.pk)
    return render(request, "upload.html")

def result_view(request, pk):
    rec = get_object_or_404(OCRResult, pk=pk)
    return render(request, "result.html", {"rec": rec})
