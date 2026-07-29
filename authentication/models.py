from django.conf import settings
from django.db import models


class NotificationSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_settings',
    )
    timezone = models.CharField(max_length=64, default='UTC')
    preferred_time = models.TimeField(default='09:00')
    expo_push_token = models.CharField(max_length=255, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} — {self.timezone} @ {self.preferred_time}'


def get_user_timezone(user) -> str:
    settings_obj = getattr(user, 'notification_settings', None)
    return settings_obj.timezone if settings_obj else 'UTC'
