from django.db import models

class OCRResult(models.Model):
    image = models.ImageField(upload_to="transcripts/")
    raw_text = models.TextField(blank=True)
    extracted = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OCRResult {self.id}"
