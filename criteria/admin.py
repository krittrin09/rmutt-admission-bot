from django.contrib import admin
from .models import MajorPermission

@admin.register(MajorPermission)
class MajorPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'major_name')
    search_fields = ('user__username', 'major_name')