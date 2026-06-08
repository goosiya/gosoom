"""스키마 공통 베이스 — camelCase 직렬화 경계(첫 도메인 슬라이스 선례).

모든 도메인 스키마는 `CamelModel`을 상속한다(architecture#Naming Patterns API).
- 내부 속성은 snake_case 유지, JSON 경계에서만 camelCase로 alias.
- `populate_by_name=True`: 클라이언트가 camel(`displayName`) 또는 snake(`display_name`) 어느 쪽으로 보내도 매핑.
- `from_attributes=True`: ORM 객체(User)를 response_model로 직접 직렬화(service의 dict 변환 불필요).
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """camelCase alias + ORM 직렬화를 기본 적용한 도메인 스키마 베이스."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
