from django.contrib import admin
from . import models
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = models.UserProfile
    can_delete = False
    verbose_name_plural = 'profile'

try:
    admin.site.unregister(User)
except Exception:
    pass

class UserAdmin(DjangoUserAdmin):
    inlines = (UserProfileInline,)

admin.site.register(User, UserAdmin)


@admin.register(models.PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'created_by', 'amount', 'created_at')
    list_filter = ('status',)


@admin.register(models.Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase_request', 'approver', 'action', 'level', 'created_at')


@admin.register(models.PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'purchase_request', 'vendor_name', 'total_amount', 'generated_at')


@admin.register(models.Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase_request', 'uploaded_by', 'validation_result', 'created_at')
