"""A wrapper around the Google Secret Manager API."""

from dataclasses import dataclass
import logging
import typing

from google.api_core import exceptions as google_exceptions
from google.cloud import secretmanager
from google.cloud.secretmanager_v1.types import resources as google_types


logger = logging.getLogger(__name__)


class SecretManagerException(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Secret:
    name: str
    creation_timestamp: int
    value: str


class SecretManagerBackend:
    @property
    def _gcp_client(self) -> secretmanager.SecretManagerServiceClient:
        if not hasattr(self, "_gcp_client_instance"):
            self._gcp_client_instance = secretmanager.SecretManagerServiceClient(transport="rest")
        return self._gcp_client_instance

    def _get_secret_version(self, name: str) -> str:
        request = secretmanager.AccessSecretVersionRequest(name=name)
        return self._gcp_client.access_secret_version(request=request).payload.data.decode()

    def _get_all_secret_versions(self, secret_name: str) -> typing.Generator[google_types.SecretVersion]:
        token = None
        while token != "":
            try:
                page = self._gcp_client.list_secret_versions(
                    request=secretmanager.ListSecretVersionsRequest(
                        parent=secret_name,
                        page_token=token,
                    ),
                )
            except ValueError as exc:
                raise ValueError("could not retrieve versions list from gcp") from exc

            yield from page

            token = page.next_page_token

    def get_last_secret_versions(self, secret_name: str) -> typing.Generator[Secret]:
        try:
            for version in self._get_all_secret_versions(secret_name):
                if version.state != google_types.SecretVersion.State.ENABLED:
                    # ignore DISABLED and DESTROYED versions
                    continue
                try:
                    yield Secret(
                        name=version.name,
                        creation_timestamp=int(version.create_time.timestamp()),
                        value=self._get_secret_version(name=version.name),
                    )
                except google_exceptions.BadRequest:
                    # The secret has been DISABLED or DESTROYED since last call to self._get_all_secret_versions
                    continue

        except Exception as exp:
            logger.exception("Error while extracting versions")  # nosemgrep
            raise SecretManagerException() from exp
