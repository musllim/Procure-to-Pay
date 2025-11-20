from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class UserProfile(models.Model):
    ROLE_STAFF = 'staff'
    ROLE_APPROVER_L1 = 'approver_level_1'
    ROLE_APPROVER_L2 = 'approver_level_2'
    ROLE_FINANCE = 'finance'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_STAFF, 'Staff'),
        (ROLE_APPROVER_L1, 'Approver Level 1'),
        (ROLE_APPROVER_L2, 'Approver Level 2'),
        (ROLE_FINANCE, 'Finance'),
        (ROLE_ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_STAFF)

    def __str__(self):
        return f"{self.user.username} ({self.role})"



class PurchaseRequest(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requests')
    proforma = models.FileField(upload_to='proformas/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PR#{self.pk} {self.title} ({self.status})"


class RequestItem(models.Model):
    purchase_request = models.ForeignKey(PurchaseRequest, related_name='items', on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def total_price(self):
        return self.quantity * self.unit_price


class Approval(models.Model):
    ACTION_APPROVED = 'APPROVED'
    ACTION_REJECTED = 'REJECTED'

    purchase_request = models.ForeignKey(PurchaseRequest, related_name='approvals', on_delete=models.CASCADE)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    level = models.PositiveSmallIntegerField()
    action = models.CharField(max_length=20)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Approval PR#{self.purchase_request_id} by {self.approver_id} ({self.action})"


class PurchaseOrder(models.Model):
    purchase_request = models.OneToOneField(PurchaseRequest, related_name='purchase_order', on_delete=models.CASCADE)
    vendor_name = models.CharField(max_length=255, blank=True)
    items = models.JSONField(default=list, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    po_number = models.CharField(max_length=64, unique=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    po_document = models.FileField(upload_to='purchase_orders/', null=True, blank=True)

    def __str__(self):
        return f"PO {self.po_number} for PR#{self.purchase_request_id}"


class Receipt(models.Model):
    purchase_request = models.ForeignKey(PurchaseRequest, related_name='receipts', on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='receipts/')
    extracted_data = models.JSONField(default=dict, blank=True)
    validation_result = models.CharField(max_length=32, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Document(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    type = models.CharField(max_length=32)
    file = models.FileField(upload_to='documents/')
    extracted_data = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
