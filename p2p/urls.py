from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import PurchaseRequestViewSet

router = DefaultRouter()
router.register(r'requests', PurchaseRequestViewSet, basename='requests')

urlpatterns = [
    path('', include(router.urls)),
]
