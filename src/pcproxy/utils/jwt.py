import base64
import json
import logging
from typing import Annotated

import fastapi
import jwt

from pcproxy import settings
from pcproxy.utils.secret_manager import SecretManagerBackend
from pcproxy.utils.secret_manager import SecretManagerException


logger = logging.getLogger(__name__)


class JwtManager:
    _key_by_kid: dict[str, str]

    def __init__(self) -> None:
        if not (settings.JWT_SECRET_KEY or settings.JWT_KEY_SECRET_NAME):
            raise RuntimeError(
                "Environment variable 'JWT_SECRET_KEY' or 'JWT_KEY_SECRET_NAME' are required but not set."
            )

        if settings.JWT_KEY_SECRET_NAME:
            self._update_internal_dict()
        else:
            self._key_by_kid = {}

    def _get_key_for_token(self, token: str) -> str:
        split = token.split(".")
        if not len(split) == 3:
            raise jwt.exceptions.InvalidTokenError("jwt %s is not a valid jwt" % token)

        # add padding to make it compatible with b64decode: a base64 string length must be
        # a multiple of 4 and the padding must be done with the symbole '='
        padding = "=" * ((4 - (len(split[0]) % 4)) % 4)

        try:
            raw_headers = base64.b64decode(split[0] + padding)
            headers = json.loads(raw_headers)
        except Exception as exc:
            raise jwt.exceptions.InvalidTokenError("jwt header %s could not be decoded" % split[0]) from exc

        if "kid" not in headers and settings.JWT_SECRET_KEY:
            return settings.JWT_SECRET_KEY

        key = self._key_by_kid.get(headers["kid"], "")

        if not key:
            raise jwt.exceptions.InvalidKeyError("jwt header %s has an unknown kid" % split[0])

        return key

    def _update_internal_dict(self) -> None:
        secret_manager_backend = SecretManagerBackend()

        try:
            secret_generator = secret_manager_backend.get_last_secret_versions(settings.JWT_KEY_SECRET_NAME)
            self._key_by_kid = {str(s.creation_timestamp): s.value for s in secret_generator}
        except SecretManagerException:
            self._key_by_kid = {}
            logger.exception("Error while building jwt keyring")

    def decode(self, jwt_token: str) -> dict:
        return jwt.decode(
            jwt_token,
            self._get_key_for_token(jwt_token),
            algorithms=["HS256"],
        )


JWT_MANAGER = JwtManager()


async def JWTUserId(authorization: Annotated[str | None, fastapi.Header()] = None) -> int | None:
    user_id = None
    if authorization and len(authorization) > 8:
        try:
            token = JWT_MANAGER.decode(
                authorization[7:],  # remove "Bearer "
            )
        except jwt.exceptions.ExpiredSignatureError:
            raise fastapi.HTTPException(status_code=401, detail="Expired JWT")
        except jwt.exceptions.InvalidSignatureError:
            raise fastapi.HTTPException(status_code=401, detail="Invalid JWT")
        except Exception:
            raise fastapi.HTTPException(status_code=401, detail="Invalid JWT")

        user_id = token.get("sub", None)

    return user_id
