"""
Обёртка над Merchant API и Web Client API.

Предоставляет класс ``MerchantBridge`` для взаимодействия
с Merchant API SDK (``msdk/``) — капча, регистрация,
профиль, поиск клиентов.
"""
import os
import sys
from typing import Any, Dict

try:
    from msdk.merchant_api import MerchantApiClient, WebClientApiClient
except ModuleNotFoundError as exc:
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    local_sdk_path = os.getenv("MERCHANT_SDK_PATH", os.path.join(workspace_root, "msdk"))
    if os.path.isdir(local_sdk_path):
        sys.path.insert(0, local_sdk_path)
        try:
            from msdk.merchant_api import MerchantApiClient, WebClientApiClient
        except ModuleNotFoundError as second_exc:
            raise RuntimeError(
                "merchant_api package not installed. Install merchant-api-sdk-python or set MERCHANT_SDK_PATH."
            ) from second_exc
    else:
        raise RuntimeError(
            "merchant_api package not installed. Install merchant-api-sdk-python or set MERCHANT_SDK_PATH."
        ) from exc


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class MerchantBridge:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_secret: str,
        use_tor: bool = True,
        tor_proxy: str | None = None,
    ):
        self.merchant_client = MerchantApiClient(
            base_url=base_url,
            api_key=api_key,
            api_secret=api_secret,
            use_tor=use_tor,
            tor_proxy=tor_proxy,
        )
        self.web_client = WebClientApiClient(
            base_url=base_url,
            api_key=api_key,
            use_tor=use_tor,
            tor_proxy=tor_proxy,
        )

    @classmethod
    def from_env(cls) -> "MerchantBridge":
        base_url = _require_env("MERCHANT_API_BASE_URL")
        api_key = _require_env("MERCHANT_API_KEY")
        api_secret = _require_env("MERCHANT_API_SECRET")
        use_tor = _env_bool("MERCHANT_USE_TOR", True)
        tor_proxy = os.getenv("MERCHANT_TOR_PROXY")
        return cls(base_url, api_key, api_secret, use_tor, tor_proxy)

    def get_captcha(self) -> Dict[str, Any]:
        return self.web_client.get_captcha()

    def register_web_client(self, captcha_id: str, captcha_answer: str) -> Dict[str, Any]:
        result = self.web_client.register(captcha_id, captcha_answer)
        profile = self.web_client.get_profile()
        data = profile.get("data", profile)
        return {
            "auth_code": result.get("auth_code"),
            "token": result.get("token"),
            "profile": data,
        }

    def get_profile(self, session_token: str) -> Dict[str, Any]:
        self.web_client.set_session_token(session_token)
        profile = self.web_client.get_profile()
        return profile.get("data", profile)

    def login_web_client(self, auth_code: str, captcha_id: str, captcha_answer: str) -> Dict[str, Any]:
        result = self.web_client.login(auth_code, captcha_id, captcha_answer)
        profile = self.web_client.get_profile()
        data = profile.get("data", profile)
        return {
            "auth_code": result.get("auth_code"),
            "token": result.get("token"),
            "profile": data,
        }

    def search_clients(self, query: str, limit: int = 10) -> Dict[str, Any]:
        return self.merchant_client.search_clients(query, limit=limit)
