from fastapi import APIRouter

from app.api.v1.admin.routes.media.confirm_upload import (
    router as confirm_upload_router,
)
from app.api.v1.admin.routes.media.create_upload import (
    router as create_upload_router,
)
from app.api.v1.admin.routes.media.delete_media import (
    router as delete_media_router,
)

router = APIRouter(prefix="/media", tags=["Media Upload"])

router.include_router(create_upload_router)
router.include_router(confirm_upload_router)
router.include_router(delete_media_router)
