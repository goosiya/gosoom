"""헬스 엔드포인트 테스트 (AC1).

라우팅·응답 형식을 격리 검증한다(get_db는 conftest에서 가짜 세션으로 override).
실제 DB 연결 검증은 AC1 라이브 점검에서 별도 수행.
"""

from httpx import AsyncClient


async def test_health_returns_200(client: AsyncClient) -> None:
    res = await client.get("/api/v1/health")
    assert res.status_code == 200


async def test_health_body_shape(client: AsyncClient) -> None:
    res = await client.get("/api/v1/health")
    body = res.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
