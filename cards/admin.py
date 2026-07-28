from django.contrib import admin

from .models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'card_type', 'status', 'interval_index', 'next_review_at')
    list_filter = ('card_type', 'status')
    search_fields = ('question',)
