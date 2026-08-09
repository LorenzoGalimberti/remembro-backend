from rest_framework.routers import DefaultRouter
from .views import CardViewSet

router = DefaultRouter()
router.register('', CardViewSet, basename='card')

urlpatterns = router.urls
