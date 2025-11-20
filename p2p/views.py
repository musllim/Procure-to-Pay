from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import models, serializers

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample
from . import serializers as local_serializers


@extend_schema(responses=local_serializers.HealthSerializer, description='Public health check')
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Simple health check for load balancers and uptime monitors."""
    data = {
        'status': 'ok',
        'service': 'procure-to-pay',
    }
    return Response(data)


from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model


class TokenObtainPairViewCustom(TokenObtainPairView):
    """Wrapper in case we want to customize later (keeps import path stable)."""
    pass


@extend_schema(responses=local_serializers.UserSerializer)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Return authenticated user info including role."""
    from .serializers import UserSerializer

    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@extend_schema(
    request=local_serializers.RoleAssignSerializer,
    responses={200: local_serializers.RoleAssignResponseSerializer},
    description='Admin endpoint to assign role to a user. Staff only.'
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_role(request):
    """Admin endpoint to assign role to a user. Only accessible by staff/superuser."""
    if not request.user.is_staff:
        return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    from .serializers import RoleAssignSerializer
    serializer = RoleAssignSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user_id = serializer.validated_data['user_id']
    role = serializer.validated_data['role']
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    profile = getattr(user, 'profile', None)
    if not profile:
        from .models import UserProfile
        profile = UserProfile.objects.create(user=user, role=role)
    else:
        profile.role = role
        profile.save()
    return Response({'detail': 'role assigned', 'user_id': user_id, 'role': role})


class PurchaseRequestViewSet(viewsets.ModelViewSet):
    queryset = models.PurchaseRequest.objects.all().order_by('-created_at')
    serializer_class = serializers.PurchaseRequestSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        request=serializers.PurchaseRequestMultipartSerializer,
        responses={201: serializers.PurchaseRequestSerializer},
        examples=[
            OpenApiExample(
                'CreatePRMultipart',
                summary='Create purchase request (multipart) example',
                value={
                    'title': 'New office chair',
                    'description': 'Ergonomic chair for dev',
                    'amount': '250.00',
                    'currency': 'USD',
                    'items': '[{"description":"Ergonomic chair","quantity":1,"unit_price":"250.00"}]',
                    'proforma': '<file>'
                },
                request_only=True,
            )
        ],
        description='Accepts multipart/form-data with `proforma` file and `items` as JSON string (recommended).',
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(created_by=user)

    @extend_schema(
        request=local_serializers.ApproveActionSerializer,
        responses={200: OpenApiExample('ApproveResponse', value={'status': 'APPROVED'})},
        examples=[
            OpenApiExample(
                'ApproveExample',
                summary='Approve PR level 2',
                value={'level': 2, 'comment': 'Approved for procurement'},
                request_only=True,
            )
        ],
        description='Approve a purchase request (requires approver role / staff).',
    )
    @action(detail=True, methods=['patch'], url_path='approve')
    def approve(self, request, pk=None):
        pr = self.get_object()
        # simple role check: only staff users can approve in this scaffold
        if not request.user.is_staff:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            pr = models.PurchaseRequest.objects.select_for_update().get(pk=pr.pk)
            if pr.status != models.PurchaseRequest.STATUS_PENDING:
                return Response({'detail': 'PurchaseRequest already processed'}, status=status.HTTP_409_CONFLICT)
            # create Approval record
            level = int(request.data.get('level', 1))
            comment = request.data.get('comment', '')
            models.Approval.objects.create(purchase_request=pr, approver=request.user, level=level, action=models.Approval.ACTION_APPROVED, comment=comment)
            # For scaffold: if level >=2 mark approved (simulate multi-level)
            if level >= 2:
                pr.status = models.PurchaseRequest.STATUS_APPROVED
                # create PO placeholder
                po = models.PurchaseOrder.objects.create(purchase_request=pr, po_number=f'PO-{pr.pk}-{level}', total_amount=pr.amount)
                pr.save()
            else:
                # leave pending for next approver
                pr.save()
        return Response({'status': pr.status})

    @action(detail=True, methods=['patch'], url_path='reject')
    def reject(self, request, pk=None):
        pr = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        reason = request.data.get('reason')
        if not reason:
            return Response({'detail': 'reason required'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            pr = models.PurchaseRequest.objects.select_for_update().get(pk=pr.pk)
            if pr.status != models.PurchaseRequest.STATUS_PENDING:
                return Response({'detail': 'PurchaseRequest already processed'}, status=status.HTTP_409_CONFLICT)
            models.Approval.objects.create(purchase_request=pr, approver=request.user, level=int(request.data.get('level', 1)), action=models.Approval.ACTION_REJECTED, comment=reason)
            pr.status = models.PurchaseRequest.STATUS_REJECTED
            pr.save()

        return Response({'status': pr.status})

    @action(detail=True, methods=['post'], url_path='submit-receipt')
    def submit_receipt(self, request, pk=None):
        pr = self.get_object()
        # Only staff (uploader) can submit receipt for approved PRs — document this
        # Actual file is provided as multipart/form-data under 'receipt'.
        if pr.status != models.PurchaseRequest.STATUS_APPROVED:
            return Response({'detail': 'Receipt can only be submitted for approved requests'}, status=status.HTTP_400_BAD_REQUEST)
        file_obj = request.FILES.get('receipt')
        if not file_obj:
            return Response({'detail': 'No receipt file provided'}, status=status.HTTP_400_BAD_REQUEST)
        receipt = models.Receipt.objects.create(purchase_request=pr, uploaded_by=request.user, file=file_obj)
        # In scaffold, set validation_result to UNVALIDATED
        receipt.validation_result = 'UNVALIDATED'
        receipt.save()
        return Response({'detail': 'Receipt submitted', 'receipt_id': receipt.pk}, status=status.HTTP_201_CREATED)




class UserViewSet(viewsets.ModelViewSet):
    """Admin/manageable User API. Staff can list/create/delete; ordinary users can view/update themselves.

    Endpoints:
    - list (staff only)
    - retrieve (self or staff)
    - create (staff only)
    - update/partial_update (self or staff)
    - destroy (staff only)
    - change_password (POST to /users/{pk}/change_password/)
    """

    User = get_user_model()
    queryset = User.objects.all().order_by('id')
    serializer_class = serializers.UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(pk=user.pk)

    def create(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        # allow users to update themselves or staff to update anyone
        target = self.get_object()
        if request.user != target and not request.user.is_staff:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    @extend_schema(
        request=serializers.PurchaseRequestMultipartSerializer,
        responses={200: serializers.PurchaseRequestSerializer},
        description='Update purchase request. Use multipart/form-data to include `proforma` file; `items` may be a JSON string.',
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='change_password')
    @extend_schema(
        request=local_serializers.ChangePasswordSerializer,
        responses={200: OpenApiExample('ChangePasswordResponse', value={'detail': 'password updated'})},
        description='Change a user password. Users must provide old_password; staff may change without old_password.'
    )
    def change_password(self, request, pk=None):
        user = self.get_object()
        # allow staff to change any password without old password; users must provide old_password
        new_password = request.data.get('new_password')
        if not new_password:
            return Response({'detail': 'new_password required'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user == user:
            old_password = request.data.get('old_password')
            if not old_password:
                return Response({'detail': 'old_password required'}, status=status.HTTP_400_BAD_REQUEST)
            if not user.check_password(old_password):
                return Response({'detail': 'old_password does not match'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)
            user.save()
            return Response({'detail': 'password updated'})

        # non-self request: only staff allowed
        if not request.user.is_staff:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        user.set_password(new_password)
        user.save()
        return Response({'detail': 'password updated by staff'})


class PurchaseOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only endpoints for Purchase Orders with a PDF download action."""

    queryset = models.PurchaseOrder.objects.all().order_by('-generated_at')
    serializer_class = serializers.PurchaseOrderSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # finance and staff can see POs; staff sees related ones, finance sees all
        user = self.request.user
        if getattr(user, 'profile', None) and user.profile.role == models.UserProfile.ROLE_FINANCE:
            return super().get_queryset()
        # non-finance: restrict to POs for PRs created by the user
        return super().get_queryset().filter(purchase_request__created_by=user)

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """Return the PO PDF; generate it if not present."""
        po = self.get_object()
        if not po.po_document:
            # generate PDF and save
            po.generate_pdf()

        # stream file
        from django.http import FileResponse
        import os

        fpath = po.po_document.path
        filename = os.path.basename(fpath)
        return FileResponse(open(fpath, 'rb'), as_attachment=True, filename=filename)


