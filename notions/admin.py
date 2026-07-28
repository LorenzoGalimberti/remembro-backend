from django.contrib import admin

from .models import Notion


@admin.register(Notion)
class NotionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'category', 'source_type', 'generation_status', 'created_at')
    list_filter = ('source_type', 'generation_status', 'category')
    search_fields = ('raw_content',)
