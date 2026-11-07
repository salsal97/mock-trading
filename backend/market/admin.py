from django.contrib import admin
from .models import Market, SpreadBid, Trade, SettlementEntry


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return {}


admin.site.register([Market, SpreadBid, Trade, SettlementEntry], ReadOnlyAdmin)
