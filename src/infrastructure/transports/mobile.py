"""
Mobile-API transport (primary).

Simulates the LinkedIn mobile client using a TLS-fingerprinted HTTP session
(curl_cffi ``impersonate``) with a stable per-account device fingerprint. This
is the low-ban-risk path that replaces headless-browser automation.

Scaffold status: the session construction (fingerprint headers, TLS
impersonation, proxy, auth material) is real and is the foundation the concrete
endpoint calls build on. The individual actions currently raise
``TransportUnavailable`` so the composite router transparently falls back to
Playwright until each mobile endpoint is implemented and validated against a
live account. Each method is a clearly-marked slot for that work.
"""

from __future__ import annotations

from typing import Any, Optional

from src.infrastructure.transports.base import (
    TransportResult,
    TransportUnavailable,
)
from src.infrastructure.transports.fingerprints import generate_fingerprint


class MobileAPITransport:
    name = "mobile"

    def __init__(self, session_factory=None):
        # session_factory injectable for tests; defaults to a curl_cffi session.
        self._session_factory = session_factory

    def _fingerprint(self, account: Any) -> dict:
        fp = getattr(account, "device_fingerprint", None)
        if fp:
            return fp
        return generate_fingerprint(str(getattr(account, "id", "unknown")))

    def build_session(self, account: Any):
        """
        Construct a TLS-fingerprinted HTTP session for the account.

        Real foundation: applies the device user-agent, LinkedIn app headers,
        TLS impersonation profile, proxy and auth material. Returned session is
        what the endpoint calls (to be implemented) will use.
        """
        if self._session_factory is not None:
            return self._session_factory(account)

        # Lazy import so environments without curl_cffi (e.g. unit tests that
        # inject a session_factory) don't require it.
        from curl_cffi import requests as cffi_requests  # type: ignore

        fp = self._fingerprint(account)
        headers = {
            "User-Agent": fp["user_agent"],
            "Accept-Language": fp.get("locale", "en_US").replace("_", "-"),
            "X-LI-Device-Id": fp["device_id"],
            "X-LI-App-Version": fp["app_version"],
            "X-LI-Platform": fp["platform"],
        }
        auth_blob = getattr(account, "auth_blob", None)
        if auth_blob:
            # auth_blob is decrypted upstream; a li_at cookie is typical.
            headers["Cookie"] = auth_blob if "=" in str(auth_blob) else f"li_at={auth_blob}"

        proxies = None
        proxy = getattr(account, "proxy", None)
        if proxy and isinstance(proxy, dict) and proxy.get("url"):
            proxies = {"http": proxy["url"], "https": proxy["url"]}

        return cffi_requests.Session(
            impersonate=fp.get("tls_impersonate", "chrome120"),
            headers=headers,
            proxies=proxies,
        )

    # --- Actions: scaffold slots. Each falls back until implemented. ---

    async def _not_yet(self, action: str) -> TransportResult:
        raise TransportUnavailable(f"mobile endpoint not yet implemented: {action}")

    async def like(self, account: Any, activity_urn: str) -> TransportResult:
        return await self._not_yet("like")

    async def comment(self, account: Any, activity_urn: str, text: str) -> TransportResult:
        return await self._not_yet("comment")

    async def follow(self, account: Any, member_urn: str) -> TransportResult:
        return await self._not_yet("follow")

    async def connect(self, account: Any, member_urn: str, note: Optional[str] = None) -> TransportResult:
        return await self._not_yet("connect")

    async def send_message(self, account: Any, member_urn: str, text: str) -> TransportResult:
        return await self._not_yet("send_message")

    async def create_post(self, account: Any, body: str, media: Any = None) -> TransportResult:
        return await self._not_yet("create_post")

    async def fetch_activity(self, account: Any, member_urn: str) -> TransportResult:
        return await self._not_yet("fetch_activity")

    async def fetch_inbox(self, account: Any, since: Any = None) -> TransportResult:
        return await self._not_yet("fetch_inbox")

    async def whoami(self, account: Any) -> TransportResult:
        return await self._not_yet("whoami")
