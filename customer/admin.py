from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from .models import ActiveClient, Client, Domain, UserClientRole

@admin.register(Client)
class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
        list_display = ('name', 'paid_until')

@admin.register(Domain)
class DomainAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('domain', 'is_primary', 'tenant')

@admin.register(ActiveClient)
class ActiveClientAdmin(admin.ModelAdmin):
    list_display = ('user', 'client')

@admin.register(UserClientRole)
class UserClientRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'client', 'role')
