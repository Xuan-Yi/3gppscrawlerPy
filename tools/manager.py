import asyncio
import os
import logging
from functools import partial
from .models import TDoc, DocType
from .network import AsyncNetworkClient, NetworkError
from .storage import StorageManager

logger = logging.getLogger(__name__)


class AsyncTDocManager:
    """
    Orchestrates check / download / extract / convert operations for 3GPP TRs and TSs.
    Each phase is exposed as a separate method to support the CLI's phase-separated pipeline.
    """

    def __init__(self, network: AsyncNetworkClient):
        self.network = network
        self.storage = StorageManager()

    # ------------------------------------------------------------------ phase 1

    async def check_tr(self, tr_number: str, doc_type: DocType = "TR") -> dict:
        """
        Check the remote archive for the latest version of a TR or TS.
        Returns a status dict:
          status: 'found' | 'not_found' | 'error'
        """
        tr = TDoc(tr_number, doc_type)
        try:
            latest_info = await self.network.get_latest_tr_version(tr)
        except NetworkError as e:
            logger.error("Network error checking %s %s: %s", doc_type, tr_number, e)
            return {"status": "error", "tr": tr_number, "doc_type": doc_type, "error": str(e)}

        if not latest_info:
            return {"status": "not_found", "tr": tr_number, "doc_type": doc_type}

        latest_filename, latest_url, latest_version = latest_info
        local_version = self.storage.get_local_tr_version(tr)
        update_available = not local_version or local_version < latest_version

        return {
            "status": "found",
            "tr": tr_number,
            "doc_type": doc_type,
            "latest_version": latest_version,
            "latest_filename": latest_filename,
            "latest_url": latest_url,
            "local_version": local_version,
            "update_available": update_available,
        }

    # ------------------------------------------------------------------ phase 2

    async def download_tr(self, tr_info: dict, bar_position: int = 0) -> bool:
        """
        Download the TR zip if an update is available.
        Returns True on success (including when no download is needed).
        """
        if not tr_info.get("update_available"):
            return True

        filename = tr_info["latest_filename"]
        url = tr_info["latest_url"]
        doc_type = tr_info["doc_type"]
        dest_path = self.storage.get_local_path(filename, doc_type)

        logger.info("Downloading %s %s (version %s)...", tr_info["doc_type"], tr_info["tr"], tr_info["latest_version"])
        try:
            await self.network.download_file(url, dest_path, bar_position=bar_position)
            return True
        except NetworkError as e:
            logger.error("Download failed for %s: %s", tr_info["tr"], e)
            return False

    # ------------------------------------------------------------------ phase 3

    def extract_tr(self, tr_info: dict, force_extract: bool, no_extract: bool, export_pdf: bool) -> bool:
        """
        Extract the TR zip. Intended to run in a thread-pool executor.
        Returns True on success or when extraction is not required.
        """
        filename = tr_info["latest_filename"]
        doc_type = tr_info["doc_type"]
        base_name = os.path.splitext(filename)[0]
        local_zip_path = self.storage.get_local_path(filename, doc_type)
        source_exists = self.storage.find_source_doc(base_name, doc_type) is not None
        pdf_exists = self.storage.find_pdf(base_name, doc_type) is not None

        if force_extract:
            should_extract = True
        elif tr_info.get("update_available"):
            should_extract = not no_extract or export_pdf
        elif export_pdf:
            should_extract = not source_exists and not pdf_exists
        else:
            should_extract = False

        if not should_extract:
            if export_pdf and (source_exists or pdf_exists):
                logger.info("Source or PDF for %s already exists; skipping extraction.", tr_info["tr"])
            return True

        if not os.path.exists(local_zip_path):
            logger.error("Zip not found for %s; cannot extract.", tr_info["tr"])
            return False

        return self.storage.extract_zip(filename, doc_type)

    # ------------------------------------------------------------------ phase 4

    def convert_tr(self, tr_info: dict) -> bool:
        """
        Convert the TR source doc to PDF. Intended to run in a thread-pool executor.
        Returns True on success.
        """
        return self.storage.export_doc_to_pdf(tr_info["latest_filename"], tr_info["doc_type"])

    # ------------------------------------------------------------------ async helpers

    async def run_in_executor(self, func, *args):
        """Run a sync callable in the default thread-pool executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args))
