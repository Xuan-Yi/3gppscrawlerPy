from .models import TR
from .network import NetworkClient
from .storage import StorageManager
import os

class TRManager:
    def __init__(self):
        self.network = NetworkClient()
        self.storage = StorageManager()

    def check_tr(self, tr_number):
        """
        Checks status of a TR. 
        Returns dict with status info.
        """
        tr = TR(tr_number)
        latest_info = self.network.get_latest_tr_version(tr)
        
        if not latest_info:
            return {"status": "not_found", "tr": tr_number}

        latest_filename, latest_url, latest_version = latest_info
        local_version = self.storage.get_local_tr_version(tr)

        update_available = False
        if not local_version or local_version < latest_version:
            update_available = True

        return {
            "status": "found",
            "tr": tr_number,
            "latest_version": latest_version,
            "latest_filename": latest_filename,
            "latest_url": latest_url,
            "local_version": local_version,
            "update_available": update_available
        }

    def update_tr(self, tr_info, force_extract=False, no_extract=False, export_pdf=False):
        """
        Downloads and processes the TR based on info from check_tr.
        """
        if not tr_info.get("update_available") and not force_extract and not export_pdf:
            return

        filename = tr_info["latest_filename"]
        url = tr_info["latest_url"]
        local_zip_path = self.storage.get_local_path(filename)
        
        # 1. Download if update available
        if tr_info.get("update_available"):
            print(f"Updating {tr_info['tr']} to version {tr_info['latest_version']}")
            self.network.download_file(url, local_zip_path)
        
        # 2. Determine if extraction is needed
        base_name = os.path.splitext(filename)[0]
        # Check if source doc already exists
        doc_path = self.storage.get_local_path(f"{base_name}.doc")
        docx_path = self.storage.get_local_path(f"{base_name}.docx")
        source_exists = os.path.exists(doc_path) or os.path.exists(docx_path)

        should_extract = False
        
        if force_extract:
            should_extract = True
        elif tr_info.get("update_available"):
            # If updated, we prefer to extract unless explicitly forbidden.
            # However, if export_pdf is set, we ignore no_extract.
            if not no_extract or export_pdf:
                should_extract = True
        elif export_pdf:
            # Not an update. Only extract if we don't have the source file.
            if not source_exists:
                should_extract = True
            else:
                print(f"Source file for {tr_info['tr']} exists, skipping extraction.")

        # 3. Ensure we have the zip if we need to extract
        if should_extract and not os.path.exists(local_zip_path):
             print(f"Downloading {filename} for extraction...")
             if not self.network.download_file(url, local_zip_path):
                 print("Download failed, cannot extract.")
                 should_extract = False

        # 4. Extract
        if should_extract:
            if no_extract and not export_pdf and not force_extract:
                 print("Extraction skipped (no-extract).")
            else:
                self.storage.extract_zip(filename)

        # 5. Export
        if export_pdf:
            self.storage.export_doc_to_pdf(filename)