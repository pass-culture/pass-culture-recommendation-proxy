from datetime import datetime
from datetime import timedelta
from unittest import mock

from fastapi.exceptions import HTTPException
import jwt
import pytest

from pcproxy import settings
from pcproxy.utils.jwt import JWTUserId
from pcproxy.utils.jwt import JwtManager
from pcproxy.utils.secret_manager import Secret


SECRETS = {
    "1": "secret-with-id-one",
    "3": "secret-with-id-three",
    "4": "secret-with-id-four",
}


def _get_last_secret_versions(secret_name):
    for key, value in SECRETS.items():
        yield Secret(
            name=f"{secret_name}/{key}",
            creation_timestamp=int(key),
            value=value,
        )


@pytest.fixture
def secret_manager():
    secret_manager_backend = mock.MagicMock()
    secret_manager_backend.get_last_secret_versions = _get_last_secret_versions

    with mock.patch("pcproxy.utils.jwt.SecretManagerBackend", return_value=secret_manager_backend):
        yield


@pytest.mark.asyncio
async def test_token_ok():
    user_id = 123
    token = jwt.encode(
        payload={
            "iat": int((datetime.now() - timedelta(seconds=10)).timestamp()),
            "nbf": int((datetime.now() - timedelta(seconds=10)).timestamp()),
            "exp": int((datetime.now() + timedelta(seconds=10)).timestamp()),
            "sub": str(user_id),
        },
        key=settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )
    result = await JWTUserId(authorization=f"Bearer {token}")
    assert result == str(user_id)


@pytest.mark.asyncio
async def test_token_with_kid(secret_manager):
    user_id = 123
    token = jwt.encode(
        payload={
            "iat": int((datetime.now() - timedelta(seconds=10)).timestamp()),
            "nbf": int((datetime.now() - timedelta(seconds=10)).timestamp()),
            "exp": int((datetime.now() + timedelta(seconds=10)).timestamp()),
            "sub": str(user_id),
        },
        key=SECRETS["3"],
        algorithm="HS256",
        headers={"kid": "3"},
    )
    with mock.patch("pcproxy.utils.jwt.settings.JWT_KEY_SECRET_NAME", "secret/name"):
        with mock.patch("pcproxy.utils.jwt.JWT_MANAGER", JwtManager()):
            result = await JWTUserId(authorization=f"Bearer {token}")
            assert result == str(user_id)


@pytest.mark.asyncio
async def test_token_wrong_kid(secret_manager):
    user_id = 123
    token = jwt.encode(
        payload={
            "iat": int((datetime.now() - timedelta(seconds=10)).timestamp()),
            "nbf": int((datetime.now() - timedelta(seconds=10)).timestamp()),
            "exp": int((datetime.now() + timedelta(seconds=10)).timestamp()),
            "sub": str(user_id),
        },
        key=SECRETS["3"],
        algorithm="HS256",
        headers={"kid": "2"},
    )
    with mock.patch("pcproxy.utils.jwt.settings.JWT_KEY_SECRET_NAME", "secret/name"):
        with mock.patch("pcproxy.utils.jwt.JWT_MANAGER", JwtManager()):
            with pytest.raises(HTTPException) as exp_info:
                await JWTUserId(authorization=f"Bearer {token}")

                assert exp_info.value.status_code == 401
                assert exp_info.value.detail == "Invalid JWT"


@pytest.mark.asyncio
async def test_expired_token():
    token = jwt.encode(
        payload={
            "iat": int(datetime.now().timestamp()),
            "nbf": int(datetime.now().timestamp()),
            "exp": int((datetime.now() - timedelta(seconds=10)).timestamp()),
            "sub": "123",
        },
        key=settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exp_info:
        await JWTUserId(authorization=f"Bearer {token}")

    assert exp_info.value.status_code == 401
    assert exp_info.value.detail == "Expired JWT"


@pytest.mark.asyncio
async def test_invalid_token():
    token = jwt.encode(
        payload={
            "iat": int(datetime.now().timestamp()),
            "nbf": int(datetime.now().timestamp()),
            "exp": int((datetime.now() + timedelta(seconds=10)).timestamp()),
            "sub": "123",
        },
        key="INVALID_SECRET",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exp_info:
        await JWTUserId(authorization=f"Bearer {token}")

    assert exp_info.value.status_code == 401
    assert exp_info.value.detail == "Invalid JWT"


@pytest.mark.asyncio
async def test_no_token():
    result = await JWTUserId(authorization=None)
    assert result is None
