# cgpe/http/session.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import time
from seleniumbase import SB


@dataclass(frozen=True)
class SessionData:
    cookies: dict[str, str]
    user_agent: str


@dataclass
class _SessionEntry:
    link: str
    data: SessionData


def bootstrap_session_from_browser(link: str) -> SessionData:
    with SB(uc=True, headless=True) as sb:
        sb.open(link)
        sb.sleep(3)
        cookies = {c["name"]: c["value"] for c in sb.get_cookies()}
        ua = sb.execute_script("return navigator.userAgent")
        return SessionData(cookies=cookies, user_agent=ua)

class SessionPool:
    def __init__(self, bootstrapper: Callable[[str], SessionData]):
        self._bootstrapper = bootstrapper
        self._pool: dict[str, _SessionEntry] = {}

    def get(self, key: str) -> SessionData:
        return self._pool[key].data

    def has(self, key: str) -> bool:
        return key in self._pool

    def create(self, key: str, link: str, *, force: bool = False) -> SessionData:
        if key in self._pool and not force:
            return self._pool[key].data

        data = self._bootstrapper(link)
        self._pool[key] = _SessionEntry(link=link, data=data)
        return data

    def drop(self, key: str) -> None:
        self._pool.pop(key, None)

    def keys(self) -> list[str]:
        return list(self._pool.keys())

    def refresh(
        self,
        key: str,
        *,
        retries: int = 2,
        delay_s: float = 2.0,
    ) -> SessionData:

        entry = self._pool[key]
        last_exc: Exception | None = None

        for attempt in range(1, retries + 2):  # total attempts = retries + 1
            try:
                data = self._bootstrapper(entry.link)
                entry.data = data
                return data
            except Exception as e:
                last_exc = e
                if attempt <= retries:
                    time.sleep(delay_s)

        assert last_exc is not None
        raise last_exc

    def refresh_all(
        self,
        *,
        retries: int = 2,
        delay_s: float = 2.0,
        fail_fast: bool = False,
    ) -> dict[str, Exception]:

        failures: dict[str, Exception] = {}
        for key in self.keys():
            try:
                self.refresh(key, retries=retries, delay_s=delay_s)
            except Exception as e:
                failures[key] = e
                if fail_fast:
                    break
        return failures