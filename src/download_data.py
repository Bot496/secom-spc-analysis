"""Download the SECOM dataset from the UCI repository into data/raw/.

Run:  python src/download_data.py

If the download is blocked on your network, download secom.zip by hand from
https://archive.ics.uci.edu/dataset/179/secom and unzip it into data/raw/.
"""

import urllib.request
import zipfile

from config import DATA_URL, RAW_DIR

# The only files we expect inside the zip.
EXPECTED_FILES = ["secom.data", "secom_labels.data", "secom.names"]


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / "secom.zip"

    print(f"Downloading {DATA_URL}")
    urllib.request.urlretrieve(DATA_URL, zip_path)

    # Extract only the files we expect, by name.
    with zipfile.ZipFile(zip_path) as archive:
        for name in EXPECTED_FILES:
            archive.extract(name, RAW_DIR)
            print(f"  extracted {name}")

    zip_path.unlink()  # the zip is no longer needed
    print(f"Done. Files are in {RAW_DIR}")


if __name__ == "__main__":
    download()
