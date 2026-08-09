"""
Nuovo file: remembro-backend/ai_service/urls.py
"""

from django.urls import path

from .views import ChatView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
]
