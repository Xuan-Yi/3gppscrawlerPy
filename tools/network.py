import asyncio
import os
import logging
from collections.abc import Awaitable, Callable
from typing import Any
import aiohttp
from bs4 import BeautifulSoup
from tqdm import tqdm
from . import config
from .models import TDoc, TDocVersion, find_latest_version

logger = logging.getLogger(__name__)

_PAGE_TIMEOUT = aiohttp.ClientTimeout(connect=10, total=config.TIMEOUT_PAGE)
_DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(connect=10, sock_read=config.TIMEOUT_DOWNLOAD)
_RETRY_STATUSES = {429, 500, 502, 503, 504}


class NetworkError(Exception):
    """Raised when a network operation fails after all retries."""


class NotFoundError(NetworkError):
    """Raised when the remote resource returns 404."""


class AsyncNetworkClient:
    """
    Async HTTP client for 3GPP archive access.
    Use as an async context manager to manage the underlying aiohttp session.
    A semaphore limits simultaneous connections to config.MAX_CONCURRENT_REQUESTS.
    """

    def __init__(self, base_url=config.BASE_URL, headers=config.HEADERS):
        self.base_url = base_url
        self.headers = headers
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, *args):
        await self._session.close()

    # ------------------------------------------------------------------ helpers

    async def _with_retry(
        self,
        url: str,
        timeout: aiohttp.ClientTimeout,
        handle_response: Callable[[aiohttp.ClientResponse], Awaitable[Any]],
    ) -> Any:
        """
        Acquire the rate-limit semaphore then GET `url` with exponential-backoff retry.
        Passes the successful response to `handle_response` and returns its result.
        Raises NotFoundError on 404, NetworkError after all retries are exhausted.
        """
        last_exc: Exception | None = None
        backoff = config.RETRY_BACKOFF

        async with self._semaphore:
            for attempt in range(1, config.RETRY_ATTEMPTS + 1):
                try:
                    async with self._session.get(url, timeout=timeout) as response:
                        if response.status == 404:
                            raise NotFoundError(f"Not found: {url}")
                        if response.status in _RETRY_STATUSES:
                            raise aiohttp.ClientResponseError(
                                response.request_info, response.history,
                                status=response.status,
                            )
                        response.raise_for_status()
                        return await handle_response(response)
                except NotFoundError:
                    raise  # 404 is definitive — don't retry
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    last_exc = exc
                    if attempt < config.RETRY_ATTEMPTS:
                        logger.warning(
                            "Request to %s failed (attempt %d/%d): %s — retrying in %.1fs",
                            url, attempt, config.RETRY_ATTEMPTS, exc, backoff,
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2

        raise NetworkError(
            f"Failed to reach {url} after {config.RETRY_ATTEMPTS} attempts: {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------ public

    async def get_latest_tr_version(self, tr: TDoc):
        """
        Scrape the 3GPP archive page to find the latest version of a TR.
        Returns (filename, url, TDocVersion) if found, None if no files are listed.
        Raises NetworkError on connectivity failure.
        """
        tr_url = f"{self.base_url}{tr.series}/{tr.number}/"
        try:
            text = await self._with_retry(tr_url, _PAGE_TIMEOUT, lambda r: r.text())
        except NotFoundError:
            return None

        soup = BeautifulSoup(text, "html.parser")
        hrefs = (link["href"] for link in soup.find_all("a", href=True))
        latest_v_tuple = find_latest_version(tr.get_filename_pattern(), hrefs)
        if not latest_v_tuple:
            return None

        latest_filename = tr.format_filename(latest_v_tuple)
        return latest_filename, tr_url + latest_filename, TDocVersion(latest_v_tuple)

    async def download_file(self, url: str, dest_path: str, bar_position: int = 0) -> None:
        """
        Stream-download a file with a tqdm progress bar.
        bar_position controls which terminal row the bar occupies (for parallel bars).
        Raises NetworkError on failure after all retries.
        """
        filename = os.path.basename(dest_path)

        async def _stream(response: aiohttp.ClientResponse) -> None:
            total_size = int(response.headers.get("content-length", 0))
            with tqdm(
                total=total_size, unit="B", unit_scale=True,
                desc=filename, position=bar_position, leave=True,
            ) as pbar:
                with open(dest_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(512 * 1024):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

        await self._with_retry(url, _DOWNLOAD_TIMEOUT, _stream)
