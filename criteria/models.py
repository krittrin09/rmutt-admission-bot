from django.db import models
from django.contrib.auth.models import User

class MajorPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ผู้ใช้งาน")
    major_name = models.CharField(max_length=200, verbose_name="ชื่อสาขาวิชา")

    def __str__(self):
        return f"{self.user.username} -> {self.major_name}"