import os
import re
import zipfile
from . import config
from .models import TR, TRVersion

class StorageManager:
    def __init__(self, local_folder=config.LOCAL_FOLDER):
        self.local_folder = local_folder
        if not os.path.exists(self.local_folder):
            os.makedirs(self.local_folder)

    def get_local_path(self, filename):
        return os.path.join(self.local_folder, filename)

    def get_local_tr_version(self, tr: TR):
        """Check the latest TR version available in the local folder."""
        pattern = tr.get_filename_pattern()
        versions = []
        
        if not os.path.exists(self.local_folder):
            return None

        for filename in os.listdir(self.local_folder):
            m = re.search(pattern, filename, re.IGNORECASE)
            if m:
                versions.append(m.groups())

        if not versions:
            return None

        latest_v_tuple = max(versions, key=lambda v: TRVersion(v))
        return TRVersion(latest_v_tuple)

    def extract_zip(self, filename):
        """Extract the contents of a zip file."""
        zip_path = self.get_local_path(filename)
        # Assuming filename ends in .zip, we want to extract to local folder
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(self.local_folder)
                print(f"Extracted {filename} successfully.")
            # Delete zip after extraction
            os.remove(zip_path)
            print(f"Deleted {filename} after extraction.")
        except zipfile.BadZipFile:
            print(f"Error: {filename} is not a valid zip file.")
        except FileNotFoundError:
            print(f"Error: File {filename} not found.")
        except PermissionError as e:
            print(f"Warning: Permission denied while extracting {filename}: {e}")
            print("Target file might be in use. Continuing without re-extraction.")

    def export_doc_to_pdf(self, filename):
        """Convert a .docx file to .pdf format using docx2pdf."""
        import docx2pdf
        
        base_name = os.path.splitext(filename)[0]
        docx_path = self.get_local_path(f"{base_name}.docx")
        pdf_path = self.get_local_path(f"{base_name}.pdf")
        
        if not os.path.exists(docx_path):
             # Try .doc as well, though docx2pdf primary focus is .docx
             doc_path = self.get_local_path(f"{base_name}.doc")
             if os.path.exists(doc_path):
                 docx_path = doc_path
             else:
                 print(f"No .doc or .docx found for {base_name}")
                 return

        try:
            # docx2pdf on Windows (via win32com) requires absolute paths
            abs_docx_path = os.path.abspath(docx_path)
            abs_pdf_path = os.path.abspath(pdf_path)
            
            print(f"Converting {os.path.basename(docx_path)} to PDF...")
            docx2pdf.convert(abs_docx_path, abs_pdf_path)
            print(f"Converted {filename} to PDF successfully.")
            
            # Delete doc/docx after conversion
            os.remove(docx_path)
            print(f"Deleted {os.path.basename(docx_path)} after conversion.")
        except Exception as e:
            print(f"Error converting {filename} to PDF: {e}")
