from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import models, serializers

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Simple health check for load balancers and uptime monitors."""
    data = {
        'status': 'ok',
        'service': 'procure-to-pay',
    }
    return Response(data)


class PurchaseRequestViewSet(viewsets.ModelViewSet):
    queryset = models.PurchaseRequest.objects.all().order_by('-created_at')
    serializer_class = serializers.PurchaseRequestSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(created_by=user)

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
