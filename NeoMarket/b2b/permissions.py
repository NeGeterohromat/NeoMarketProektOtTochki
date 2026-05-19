from rest_framework import permissions

from app.models import ProductStatus


class CanUpdateProduct(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user != obj.seller:
            self.message = "Product does not belong to the authenticated seller"
            return False
        if obj.status == ProductStatus.HARD_BLOCKED:
            self.message = "Cannot edit hard-blocked product"
            return False
        return True
    

class CanCreateUpdateSKU(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user != obj.product.seller:
            self.message = "Product does not belong to the authenticated seller"
            return False
        if obj.product.status == ProductStatus.HARD_BLOCKED and request.method in ['PUT', 'PATCH']:
            self.message = "Cannot edit hard-blocked product"
            return False
        return True