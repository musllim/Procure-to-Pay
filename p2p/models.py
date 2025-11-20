from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
import io
import os
from django.core.files.base import ContentFile


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

    def generate_pdf(self):
        """Generate a simple PO PDF and store it in `po_document`.

        Uses ReportLab to render a basic Purchase Order containing header, vendor, items and totals.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas
        except Exception:
            raise

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Header
        c.setFont('Helvetica-Bold', 16)
        c.drawString(30 * mm, height - 30 * mm, f'Purchase Order: {self.po_number}')
        c.setFont('Helvetica', 10)
        c.drawString(30 * mm, height - 36 * mm, f'Generated: {self.generated_at.strftime("%Y-%m-%d %H:%M:%S")}')

        # Vendor
        c.setFont('Helvetica-Bold', 12)
        c.drawString(30 * mm, height - 46 * mm, 'Vendor:')
        c.setFont('Helvetica', 10)
        c.drawString(45 * mm, height - 46 * mm, self.vendor_name or '')

        # Items table header
        y = height - 60 * mm
        c.setFont('Helvetica-Bold', 10)
        c.drawString(30 * mm, y, 'Description')
        c.drawString(120 * mm, y, 'Quantity')
        c.drawString(140 * mm, y, 'Unit Price')
        c.drawString(170 * mm, y, 'Total')
        y -= 6 * mm
        c.setFont('Helvetica', 10)

        # Items
        for it in (self.items or []):
            desc = it.get('description', '')
            qty = str(it.get('quantity', ''))
            up = str(it.get('unit_price', ''))
            total = ''
            try:
                total = str(float(it.get('quantity', 0)) * float(it.get('unit_price', 0)))
            except Exception:
                total = ''
            c.drawString(30 * mm, y, desc[:60])
            c.drawString(120 * mm, y, qty)
            c.drawString(140 * mm, y, up)
            c.drawString(170 * mm, y, total)
            y -= 6 * mm
            if y < 30 * mm:
                c.showPage()
                y = height - 30 * mm

        # Totals
        c.setFont('Helvetica-Bold', 11)
        c.drawString(140 * mm, y - 6 * mm, 'Total Amount:')
        c.drawString(170 * mm, y - 6 * mm, str(self.total_amount or ''))

        c.showPage()
        c.save()

        buffer.seek(0)
        fname = f'{self.po_number}.pdf'
        content = ContentFile(buffer.read())
        # save to FileField
        self.po_document.save(fname, content, save=True)
        buffer.close()


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
