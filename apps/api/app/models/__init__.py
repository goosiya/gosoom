# SQLAlchemy 모델: user, category, service_request, quote, chat_room, message — Story 1.2~4
# alembic autogenerate가 모델을 감지하려면 여기서 import 해야 한다(env.py가 `app.models`를 로드).
from app.models.category import Category
from app.models.user import User, UserRole

__all__ = ["Category", "User", "UserRole"]
