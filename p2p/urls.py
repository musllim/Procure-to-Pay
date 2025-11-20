from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import PurchaseRequestViewSet, health_check, UserViewSet, PurchaseOrderViewSet
from .views import TokenObtainPairViewCustom, TokenRefreshView, me, assign_role

router = DefaultRouter()
router.register(r'requests', PurchaseRequestViewSet, basename='requests')
router.register(r'users', UserViewSet, basename='users')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchaseorders')

urlpatterns = [
    path('health/', health_check, name='health'),
    path('auth/token/', TokenObtainPairViewCustom.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', me, name='auth_me'),
    path('auth/assign-role/', assign_role, name='auth_assign_role'),
    path('', include(router.urls)),
]
