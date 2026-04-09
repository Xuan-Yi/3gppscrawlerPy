import os
import threading
import zipfile
import logging
from . import config
from .models import TDoc, TDocVersion, DocType, find_latest_version

logger = logging.getLogger(__name__)

_word_semaphore = threading.Semaphore(config.MAX_WORD_INSTANCES)
_WD_FORMAT_PDF = 17  # wdFormatPDF


class StorageManager:
    _FOLDERS = {"TR": config.TR_FOLDER, "TS": config.TS_FOLDER}

    def __init__(self):
        for folder in self._FOLDERS.values():
            os.makedirs(folder, exist_ok=True)

    def _doc_folder(self, doc_type: DocType) -> str:
        return self._FOLDERS[doc_type]

    def get_local_path(self, filename: str, doc_type: DocType = "TR") -> str:
        return os.path.join(self._doc_folder(doc_type), filename)

    def find_source_doc(self, base_name: str, doc_type: DocType = "TR") -> str | None:
        """Return the path to the .docx or .doc source file, or None if neither exists."""
        for ext in (".docx", ".doc"):
            path = self.get_local_path(f"{base_name}{ext}", doc_type)
            if os.path.exists(path):
                return path
        return None

    def find_pdf(self, base_name: str, doc_type: DocType = "TR") -> str | None:
        """Return the path to the .pdf file if it exists."""
        path = self.get_local_path(f"{base_name}.pdf", doc_type)
        return path if os.path.exists(path) else None

    def get_local_tr_version(self, tr: TDoc) -> TDocVersion | None:
        """Check the latest version of a TR/TS available in its local subfolder."""
        folder = self._doc_folder(tr.doc_type)
        latest = find_latest_version(tr.get_filename_pattern(), os.listdir(folder))
        return TDocVersion(latest) if latest else None

    def extract_zip(self, filename: str, doc_type: DocType = "TR") -> bool:
        """
        Extract the contents of a zip file into the doc-type subfolder.
        Deletes the zip only after confirming at least one file was extracted.
        Returns True on success, False on failure.
        """
        folder = self._doc_folder(doc_type)
        zip_path = self.get_local_path(filename, doc_type)
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                members = zip_ref.namelist()
                if not members:
                    logger.warning("Zip %s is empty; skipping extraction.", filename)
                    return False
                zip_ref.extractall(folder)
                logger.info("Extracted %s (%d file(s)).", filename, len(members))

            os.remove(zip_path)
            logger.info("Deleted %s after extraction.", filename)
            return True

        except zipfile.BadZipFile:
            logger.error("%s is not a valid zip file.", filename)
            return False
        except FileNotFoundError:
            logger.error("File %s not found.", filename)
            return False
        except PermissionError as e:
            logger.warning(
                "Permission denied while extracting %s: %s — target may be in use.",
                filename, e,
            )
            return False

    def export_doc_to_pdf(self, filename: str, doc_type: DocType = "TR") -> bool:
        """
        Convert a .docx or .doc file to PDF using Word COM automation.
        Each call initializes its own COM apartment so multiple threads can
        convert in parallel (up to MAX_WORD_INSTANCES simultaneous instances).
        Deletes the source document on success.
        Returns True on success, False on failure.
        """
        import pythoncom
        import win32com.client

        base_name = os.path.splitext(filename)[0]
        if self.find_pdf(base_name, doc_type):
            logger.info("PDF for %s already exists; skipping conversion.", base_name)
            return True

        source_path = self.find_source_doc(base_name, doc_type)
        if source_path is None:
            logger.error("No .doc or .docx found for %s", base_name)
            return False

        pdf_path = self.get_local_path(f"{base_name}.pdf", doc_type)
        abs_source = os.path.abspath(source_path)
        abs_pdf = os.path.abspath(pdf_path)
        logger.info("Converting %s to PDF...", os.path.basename(source_path))

        with _word_semaphore:
            _coinit_ok = False
            word = None
            try:
                pythoncom.CoInitialize()
                _coinit_ok = True

                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(abs_source)
                try:
                    doc.SaveAs(abs_pdf, FileFormat=_WD_FORMAT_PDF)
                finally:
                    doc.Close(SaveChanges=False)

                logger.info("Converted to PDF: %s", os.path.basename(abs_pdf))
                os.remove(source_path)
                logger.info("Deleted %s after conversion.", os.path.basename(source_path))
                return True

            except Exception as e:
                logger.error("Error converting %s to PDF: %s", filename, e)
                return False
            finally:
                if word is not None:
                    try:
                        word.Quit()
                    except Exception:
                        pass
                if _coinit_ok:
                    pythoncom.CoUninitialize()
