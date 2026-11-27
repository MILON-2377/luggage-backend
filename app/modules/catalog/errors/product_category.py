from app.core.errors.base import ConflictError, NotFoundError, ValidationError


class ProductCategoryNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Product category not found.")


class ProductCategorySlugConflictError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            "A product category with this slug already exists under the same parent."
        )


class ProductCategoryParentNotFoundError(NotFoundError):
    def __init__(self, parent_id: str) -> None:
        super().__init__(
            f"Parent product category '{parent_id}' was not found."
        )

class ProductCategoryInvalidParentError(ValidationError):
    def __init__(self) -> None:
        super().__init__("The selected parent category is not valid.")


class ProductCategoryAttributeNotFoundError(NotFoundError):
    def __init__(self, attribute_id: str) -> None:
        super().__init__(f"Product attribute '{attribute_id}' was not found.")


class ProductCategoryMediaNotFoundError(NotFoundError):
    def __init__(self, media_asset_id: str) -> None:
        super().__init__(f"Media asset '{media_asset_id}' was not found.")


class ProductCategoryMediaNotReadyError(ValidationError):
    def __init__(self, media_asset_id: str) -> None:
        super().__init__(f"Media asset '{media_asset_id}' is not ready for use.")



class ProductCategoryDuplicateAttributeError(ValidationError):
    def __init__(self) -> None:
        super().__init__(
            "Duplicate product attributes are not allowed for a category."
        )


class ProductCategoryDuplicateMediaError(ValidationError):
    def __init__(self) -> None:
        super().__init__(
            "Duplicate media assignments are not allowed for a category."
        )