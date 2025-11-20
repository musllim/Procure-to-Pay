from rest_framework import serializers
from . import models
from django.contrib.auth import get_user_model

User = get_user_model()


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


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='profile.role', read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'password')

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            # create unusable password if none provided
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RoleAssignSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=[r[0] for r in models.UserProfile.ROLE_CHOICES])


class RoleAssignResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    user_id = serializers.IntegerField()
    role = serializers.CharField()


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()


class ApproveActionSerializer(serializers.Serializer):
    level = serializers.IntegerField(required=False, default=1)
    comment = serializers.CharField(required=False, allow_blank=True)


class RejectActionSerializer(serializers.Serializer):
    level = serializers.IntegerField(required=False, default=1)
    reason = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=False, allow_blank=True)
    new_password = serializers.CharField()


class SubmitReceiptSerializer(serializers.Serializer):
    # Represented as metadata for the file upload in docs. Actual endpoint uses multipart file upload.
    note = serializers.CharField(required=False, allow_blank=True)

