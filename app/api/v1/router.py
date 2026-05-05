from fastapi import APIRouter
from app.api.v1.endpoints.admin_papers import router as admin_papers_router
from app.api.v1.endpoints.admin_users import router as admin_users_router
from app.api.v1.endpoints.admin_jobs import router as admin_jobs_router
from app.api.v1.endpoints.admin_system import router as admin_system_router
from app.api.v1.endpoints.admin_reviews import router as admin_reviews_router
from app.api.v1.endpoints.user_notes import router as user_notes_router
from app.api.v1.endpoints.user_papers import router as user_papers_router


router = APIRouter()
router.include_router(admin_papers_router, prefix="/admin/papers", tags=["admin-papers"])
router.include_router(admin_users_router, prefix="/admin", tags=["admin-users"])
router.include_router(admin_jobs_router, prefix="/admin", tags=["admin-jobs"])
router.include_router(admin_system_router, prefix="/admin", tags=["admin-system"])
router.include_router(admin_reviews_router, prefix="/admin", tags=["admin-reviews"])
router.include_router(user_notes_router, prefix="/notes", tags=["user-notes"])
router.include_router(user_papers_router, prefix="/papers", tags=["user-papers"])
