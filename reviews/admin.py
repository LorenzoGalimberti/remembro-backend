from django.contrib import admin

from .models import ReviewLog


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = ('card', 'user', 'verdict', 'reviewed_at', 'interval_before', 'interval_after')
    list_filter = ('verdict',)
