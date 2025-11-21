from django.db import models

class ProgramCriteria(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    min_gpax = models.FloatField(default=0.0)
    min_gpamath = models.FloatField(null=True, blank=True)
    min_gpasci = models.FloatField(null=True, blank=True)
    min_gpalan = models.FloatField(null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"
