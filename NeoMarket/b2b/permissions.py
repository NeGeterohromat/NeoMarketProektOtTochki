from rest_framework import permissions

from app.models import ProductStatus, Product


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
    def has_permission(self, request, view):
        if request.method == 'POST':
            product_id = request.data.get('product_id')
            if not product_id:
                return True # Позволяем сериализатору самому выкинуть ошибку 400 о пустом поле
            try:
                product = Product.objects.get(pk=product_id)
                if request.user != product.seller:
                    self.message = "Product does not belong to the authenticated seller"
                    return False
                if product.status == ProductStatus.HARD_BLOCKED:
                    self.message = "Cannot edit hard-blocked product"
                    return False
            except Product.DoesNotExist:
                return True # Позволяем сериализатору выкинуть 400 ошибку о несуществующем продукте
        return True
    
    def has_object_permission(self, request, view, obj):
        if request.user != obj.product.seller:
            self.message = "Product does not belong to the authenticated seller"
            return False
        if obj.product.status == ProductStatus.HARD_BLOCKED:
            self.message = "Cannot edit hard-blocked product"
            return False
        return True