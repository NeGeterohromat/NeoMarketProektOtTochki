from rest_framework import permissions
from rest_framework import exceptions

from app.models import ProductStatus, Product


class IsAuthenticatedOrService(permissions.BasePermission):
    """
    Разрешает доступ, если пользователь авторизован через JWT 
    ИЛИ если запрос пришел от микросервиса по X-Service-Key.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
            
        auth_data = request.auth
        if isinstance(auth_data, dict) and auth_data.get('is_moderator_service') is True:
            return True
            
        return False


class IsSafeForModerator(permissions.BasePermission):
    """Запрещает сервису модерации любые мутирующие (изменяющие) запросы."""
    message = "Сервису модерации запрещено изменять данные."

    def has_permission(self, request, view):
        is_mod = hasattr(view, 'is_moderator') and view.is_moderator()
        
        if is_mod and request.method not in permissions.SAFE_METHODS:
            return False
            
        return True
    

class IsService(permissions.BasePermission):
    """Разрешает доступ только сервисам по X-Service-Key (без JWT)."""
    message = "Service Key required"
    
    def has_permission(self, request, view):
        auth_data = request.auth
        if isinstance(auth_data, dict) and auth_data.get('is_moderator_service') is True:
            return True
        # Возвращаем False, чтобы permission_denied() сама решила, какое исключение выбросить
        return False


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