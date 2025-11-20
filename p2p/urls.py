from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import PurchaseRequestViewSet, health_check

router = DefaultRouter()
router.register(r'requests', PurchaseRequestViewSet, basename='requests')

urlpatterns = [
    path('health/', health_check, name='health'),
    path('', include(router.urls)),
]
