import os

DEFAULT_TR_LIST = [
    "38.811", "38.821", "38.863", "38.820", "38.921",
    "36.942", "38.814", "38.815", "38.901", "38.913"
]

BASE_URL = "https://www.3gpp.org/ftp/Specs/archive/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36"
}
LOCAL_FOLDER = "./3gpp_trs"

# Ensure local folder exists
if not os.path.exists(LOCAL_FOLDER):
    try:
        os.makedirs(LOCAL_FOLDER)
    except OSError:
        pass # Handle permissions or other errors gracefully in usage
