import requests
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
from . import config
from .models import TR, TRVersion

class NetworkClient:
    def __init__(self, base_url=config.BASE_URL, headers=config.HEADERS):
        self.base_url = base_url
        self.headers = headers

    def get_latest_tr_version(self, tr: TR):
        """
        Scrape the 3GPP website to find the latest version of a TR.
        Returns (filename, url, TRVersion) or None.
        """
        tr_url = f"{self.base_url}{tr.series}/{tr.number}/"

        try:
            response = requests.get(tr_url, headers=self.headers, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error: Unable to access {tr_url} ({e})")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        pattern = tr.get_filename_pattern()

        versions = []
        for link in soup.find_all("a", href=True):
            m = re.search(pattern, link["href"], re.IGNORECASE)
            if m:
                # m.groups() returns a tuple like ('f', '20')
                versions.append(m.groups())

        if not versions:
            return None

        # Find max version
        # We need to wrap them in TRVersion to compare
        latest_v_tuple = max(versions, key=lambda v: TRVersion(v))
        
        latest_filename = tr.format_filename(latest_v_tuple)
        full_url = tr_url + latest_filename
        
        return latest_filename, full_url, TRVersion(latest_v_tuple)

    def download_file(self, url, dest_path):
        """Download a file with progress bar."""
        try:
            response = requests.get(url, headers=self.headers, stream=True, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to download {url} ({e})")
            return False

        total_size = int(response.headers.get("content-length", 0))
        filename = dest_path.split("/")[-1] # Simple extraction for display
        
        with tqdm(total=total_size, unit="B", unit_scale=True, desc=filename) as pbar:
            with open(dest_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=512 * 1024):
                    if chunk:
                        pbar.update(len(chunk))
                        file.write(chunk)
        return True
