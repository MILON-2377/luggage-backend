from app.core.config import settings
from app.integrations.security.cookie_policy import CookiePolicy
from app.integrations.security.cookie_service import CookieService


def get_cookie_service() -> CookieService:
    cookie_policy = CookiePolicy(settings=settings)

    return CookieService(policy=cookie_policy)