"""
Sostituisce interamente: remembro-backend/ai_service/admin.py
Stesso stile di CardAdmin.
"""

from django.contrib import admin

from .models import AIUsageLog


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'user', 'call_type', 'model',
        'prompt_tokens', 'completion_tokens', 'reasoning_tokens', 'total_tokens',
    )
    list_filter = ('call_type', 'model')
    search_fields = ('user__username',)
