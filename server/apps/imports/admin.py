from django.contrib import admin

from .models import ImportJob


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "import_type", "status", "uploaded_by", "row_count", "error_count", "created_at")
    list_filter = ("import_type", "status")
    search_fields = ("original_filename", "uploaded_by__email")
