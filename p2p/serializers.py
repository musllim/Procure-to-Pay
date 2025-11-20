from rest_framework import serializers
from . import models


class RequestItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RequestItem
        fields = ('id', 'description', 'quantity', 'unit_price')


class PurchaseRequestSerializer(serializers.ModelSerializer):
    items = RequestItemSerializer(many=True, required=False)
    created_by = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = models.PurchaseRequest
        fields = ('id', 'title', 'description', 'amount', 'currency', 'status', 'created_by', 'items', 'proforma', 'created_at')
        read_only_fields = ('status', 'created_at')

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        pr = models.PurchaseRequest.objects.create(**validated_data)
        for item in items_data:
            models.RequestItem.objects.create(purchase_request=pr, **item)
        return pr


class ApprovalSerializer(serializers.ModelSerializer):
    approver = serializers.ReadOnlyField(source='approver.username')

    class Meta:
        model = models.Approval
        fields = ('id', 'purchase_request', 'approver', 'level', 'action', 'comment', 'created_at')
        read_only_fields = ('approver', 'created_at')
