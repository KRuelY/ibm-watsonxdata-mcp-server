"""
account-IAM authenticator for watsonx.data on non-IBM hyperscalers (Azure, AWS).

Mimics the IAMAuthenticator interface so WatsonXClient can use it
interchangeably. Token refresh and caching are handled by the base
TokenManager class from ibm-cloud-sdk-core.
"""

from __future__ import annotations

from typing import Any

from ibm_cloud_sdk_core.token_managers.token_manager import TokenManager


class AccountIAMTokenManager(TokenManager):
    """Token manager that fetches bearer tokens from account-iam.

    The account-iam endpoint returns:
        {"token": "...", "token_type": "Bearer", "expires_in": 7200, "expiration": <unix-ts>}

    Token refresh is triggered at 80% of the token lifetime, matching the
    behaviour of JWTTokenManager in the IBM SDK.
    """

    def __init__(
        self,
        apikey: str,
        service_id: str,
        host: str,
        *,
        disable_ssl_verification: bool = False,
    ) -> None:
        self.apikey = apikey
        self.service_id = service_id
        url = f"{host.rstrip('/')}/api/2.0/services/{service_id}/apikeys/token"
        super().__init__(url, disable_ssl_verification=disable_ssl_verification)

    def request_token(self) -> dict[str, Any]:  # type: ignore[override]
        """POST to account-iam and return the parsed JSON response."""
        response = self._request(
            "POST",
            self.url,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json={"apikey": self.apikey},
        )
        return response.json()

    def _save_token_info(self, token_response: dict[str, Any]) -> None:
        """Persist token and compute expiry/refresh timestamps."""
        self.access_token = token_response["token"]
        expiration: int = token_response["expiration"]
        expires_in: int = token_response.get("expires_in", 3600)
        self.expire_time = expiration
        self.refresh_time = expiration - expires_in * 0.2


class AccountIAMAuthenticator:
    """Authenticator for account-iam on non-IBM hyperscalers (Azure, AWS).

    Exposes a ``token_manager`` attribute so it can be used anywhere
    an IAMAuthenticator is expected.
    """

    def __init__(
        self,
        apikey: str,
        service_id: str,
        host: str,
        *,
        disable_ssl_verification: bool = False,
    ) -> None:
        self.token_manager = AccountIAMTokenManager(
            apikey=apikey,
            service_id=service_id,
            host=host,
            disable_ssl_verification=disable_ssl_verification,
        )
