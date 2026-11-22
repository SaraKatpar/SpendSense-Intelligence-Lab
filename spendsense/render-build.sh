#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r requirements.txt

# Native Render services have no root access. Extract Debian's OCR packages
# into the application instead of trying to install system-wide packages.
ROOT="$(pwd)/.render-ocr"
mkdir -p "$ROOT/packages" "$ROOT/lists/partial" "$ROOT/cache/archives/partial"
APT=(-o "Dir::State::lists=$ROOT/lists" -o "Dir::Cache=$ROOT/cache" -o APT::Get::List-Cleanup=0)
apt-get "${APT[@]}" update
cd "$ROOT/packages"
apt-get "${APT[@]}" download tesseract-ocr tesseract-ocr-eng libtesseract5 liblept5
for package in ./*.deb; do
    dpkg-deb -x "$package" "$ROOT"
done
LD_LIBRARY_PATH="$ROOT/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}" "$ROOT/usr/bin/tesseract" --version
