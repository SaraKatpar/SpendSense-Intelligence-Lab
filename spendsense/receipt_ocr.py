"""SpendSense receipt OCR. Estimates only; user must review before saving."""
import io
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 30_000_000
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
LABELS = [
    (r'\b(?:grand\s+total|net\s+total|net\s+payable|amount\s+due|amount\s+payable|balance\s+due|total\s+payable|total\s+amount)\b', 3),
    (r'\btotal\b', 2),
]
AMOUNT = re.compile(r'(?<![\w.,])(?:PKR\s*|Rs\.?\s*|[$£€]\s*)?(\d{1,3}(?:[,.]\d{3})+(?:[,.]\d{2})?|\d+(?:[.,]\d{1,2})?)(?![\w.,])', re.I)


def find_tesseract():
    base = Path(__file__).resolve().parent
    bundled = base / '.render-ocr'
    if (bundled / 'usr/bin/tesseract').is_file():
        libraries = str(bundled / 'usr/lib/x86_64-linux-gnu')
        if libraries not in os.environ.get('LD_LIBRARY_PATH', '').split(os.pathsep):
            os.environ['LD_LIBRARY_PATH'] = libraries + os.pathsep + os.environ.get('LD_LIBRARY_PATH', '')
        tessdata = next((bundled / 'usr/share/tesseract-ocr').glob('*/tessdata'), None)
        if tessdata:
            os.environ['TESSDATA_PREFIX'] = str(tessdata)
        return str(bundled / 'usr/bin/tesseract')
    options = [os.environ.get('TESSERACT_CMD'), shutil.which('tesseract'),
               r'C:\Program Files\Tesseract-OCR\tesseract.exe',
               r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
               str(base / 'tools' / 'tesseract' / 'tesseract.exe'),
               str(Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Tesseract-OCR' / 'tesseract.exe')]
    for path in options:
        if path and Path(path).is_file():
            return str(path)
    raise RuntimeError('Tesseract not found. Install it or set TESSERACT_CMD.')


def parse_money(raw):
    raw = raw.strip().replace(' ', '')
    if ',' in raw and '.' in raw:
        decimal = ',' if raw.rfind(',') > raw.rfind('.') else '.'
        thousands = '.' if decimal == ',' else ','
        raw = raw.replace(thousands, '').replace(decimal, '.')
    elif ',' in raw:
        parts = raw.split(',')
        if len(parts) == 2 and len(parts[-1]) in (1, 2):
            raw = raw.replace(',', '.')
        else:
            raw = raw.replace(',', '')
    elif raw.count('.') > 1:
        parts = raw.split('.')
        if len(parts[-1]) in (1, 2):
            raw = ''.join(parts[:-1]) + '.' + parts[-1]
        else:
            raw = ''.join(parts)
    return float(raw)


def extract_total(text):
    candidates = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if re.search(r'\bsub[\s-]*total\b|\btotal\s*(?:tax|gst|qty|quantity|items)\b', line, re.I):
            continue
        for label, priority in LABELS:
            match = re.search(label, line, re.I)
            if not match:
                continue
            after = line[match.end():]
            values = AMOUNT.findall(after)
            if not values and index + 1 < len(lines):
                next_line = lines[index + 1].strip()
                if re.fullmatch(r'(?:PKR\s*|Rs\.?\s*)?\d[\d,.]*', next_line, re.I):
                    values = AMOUNT.findall(next_line)
            if values:
                try:
                    amount = parse_money(values[0])
                    if np.isfinite(amount) and amount > 0:
                        candidates.append((priority, index, round(amount, 2), line))
                except ValueError:
                    pass
            break
    if not candidates:
        return None, None
    _, _, amount, line = max(candidates, key=lambda c: (c[0], c[1]))
    return amount, line


def extract_date(text):
    patterns = [
        (r'\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b', 'ymd'),
        (r'\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b', 'dmy'),
        (r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{2})\b', 'short'),
    ]
    for pattern, kind in patterns:
        for m in re.finditer(pattern, text):
            a, b, c = map(int, m.groups())
            y, mo, d = (a, b, c) if kind == 'ymd' else ((c if kind == 'dmy' else c + 2000), b, a)
            try:
                return datetime(y, mo, d).date().isoformat()
            except ValueError:
                continue
    return None


def extract_currency(text):
    for code, pattern in [
        ('PKR', r'\bPKR\b|\bRs\.?\s*\d|\brupees?\b'),
        ('USD', r'\bUSD\b|US\s*\$|\$'),
        ('EUR', r'\bEUR\b|€'),
        ('GBP', r'\bGBP\b|£'),
    ]:
        if re.search(pattern, text, re.I):
            return code
    return None


def extract_merchant(text):
    """Conservative header heuristic; uncertain headers remain blank."""
    lines = [s.strip() for s in text.splitlines() if s.strip()]
    reject = re.compile(r'\b(?:receipt|invoice|date|time|cash|change|total|tax|phone|tel|qty|item|apple|banana|orange|pear|grapes|milk|cheese|yogurt|potato|blueberry|strawberry|kiwi|lemon|watermelon|raspberry)\b', re.I)
    for line in lines[:5]:
        if reject.search(line) or len(line) > 36 or re.search(r'\d', line):
            continue
        words = re.findall(r'[A-Za-z]{2,}', line)
        if not (1 <= len(words) <= 4):
            continue
        if sum(len(w) for w in words) < 5:
            continue
        letters = ''.join(words)
        if len(letters) < 5 or len(set(letters.lower())) < 4:
            continue
        if len(re.findall(r'[^\w\s]', line)) > 1:
            continue
        # Accept a reasonably compact business-like header, not sprawling OCR noise.
        if len(line.split()) > 4:
            continue
        return line
    return None


def parse_receipt_text(text):
    text = (text or '').strip()
    merchant = extract_merchant(text)
    date = extract_date(text)
    amount, matched_line = extract_total(text)
    currency = extract_currency(text)
    missing = [key for key, value in [('merchant', merchant), ('date', date), ('amount', amount), ('currency', currency)] if value is None]
    return {
        'status': 'unreadable' if not text else 'review_required',
        'merchant': merchant,
        'date': date,
        'amount': amount,
        'currency': currency,
        'description': f'Purchase at {merchant}' if merchant else None,
        'category': None,
        'total_matched_line': matched_line,
        'missing_fields': missing,
        'raw_text': text,
        'requires_confirmation': True,
        'notes': ['OCR values are estimates; check against the image.', 'No transaction has been saved.'],
    }


def preprocess_image(image):
    image = ImageOps.exif_transpose(image).convert('RGB')
    rgb = np.array(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    if w < 1200:
        scale = min(2.5, 1200 / w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    contrast = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    binary = cv2.adaptiveThreshold(contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
    return contrast, binary


def extract_text_from_image(image):
    pytesseract.pytesseract.tesseract_cmd = find_tesseract()
    contrast, binary = preprocess_image(image)
    variants = [(image, '--psm 3'), (contrast, '--psm 6'), (binary, '--psm 6')]
    results = []
    for source, config in variants:
        text = pytesseract.image_to_string(source, lang='eng', config=config, timeout=30).strip()
        if text:
            amount, _ = extract_total(text)
            lines = [line for line in text.splitlines() if len(re.findall(r'[A-Za-z0-9]', line)) >= 3]
            # Prefer a plausible total, then coherent text over raw OCR length.
            score = (1 if amount is not None else 0, len(lines), len(text))
            results.append((score, text))
    return max(results, key=lambda item: item[0])[1] if results else ''


def scan(image_bytes):
    """Scan JPG/PNG bytes. Returns editable data; never saves it."""
    if not image_bytes:
        raise ValueError('Image is empty.')
    if len(image_bytes) > MAX_BYTES:
        raise ValueError('Receipt exceeds 8 MB.')
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            if source.format not in ('PNG', 'JPEG'):
                raise ValueError('Only JPG and PNG are supported.')
            if source.width * source.height > MAX_PIXELS:
                raise ValueError('Receipt exceeds 30 megapixels.')
            image = ImageOps.exif_transpose(source).convert('RGB')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Cannot decode receipt image.') from exc
    return parse_receipt_text(extract_text_from_image(image))


def read_receipt_text(image_path):
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f'Receipt image not found: {image_path}')
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError('Only JPG and PNG are supported.')
    return scan(path.read_bytes())['raw_text']


def scan_receipt(image_path):
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f'Receipt image not found: {image_path}')
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError('Only JPG and PNG are supported.')
    return scan(path.read_bytes())


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python receipt_ocr.py "test_receipt.png"')
        sys.exit(1)
    try:
        print(json.dumps(scan_receipt(sys.argv[1]), indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f'OCR error: {exc}', file=sys.stderr)
        sys.exit(1)
