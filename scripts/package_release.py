"""Build a minimal unpacked-extension ZIP from an explicit safe file list."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
FILES = ["manifest.json", "clipboard.js", "content.js", "content.css",
         "popup.html", "popup.js", "popup.css", "README.md"]
DESTINATION = ROOT / "dist" / "sodp-issue-reporter-extension.zip"
DESTINATION.parent.mkdir(exist_ok=True)
with ZipFile(DESTINATION, "w", compression=ZIP_DEFLATED) as archive:
    for name in FILES:
        archive.write(ROOT / name, arcname=f"sodp-issue-reporter-extension/{name}")
print(DESTINATION)
