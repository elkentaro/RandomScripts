# 📸 Webpage Screenshot Capture (Playwright)

This script captures a full-page screenshot of a webpage and saves it as a timestamped PNG image.

It is designed to be simple, reliable, and easy to automate (e.g., with cron every 5 hours).

---

## 🚀 Features

- Headless browser (no GUI required)
- Full-page screenshots (not just viewport)
- Timestamped filenames
- Works well for automation / monitoring pages

---

## 📦 Prerequisites

### 1. System packages (Linux)

```bash
sudo apt-get update
sudo apt-get install -y \
  libatk1.0-0t64 \
  libatk-bridge2.0-0t64 \
  libcups2t64 \
  libxkbcommon0 \
  libatspi2.0-0t64 \
  libxcomposite1 \
  libxdamage1 \
  libxfixes3 \
  libxrandr2 \
  libgbm1 \
  libcairo2 \
  libpango-1.0-0
```

### 2. Python (recommended: 3.10–3.12)

```bash
python3 --version
```

---

## 🛠️ Installation

```bash
mkdir -p /mnt/usb/screencap
cd /mnt/usb/screencap

python3 -m venv venv
source venv/bin/activate

pip install playwright
python -m playwright install chromium

sudo /mnt/usb/screencap/venv/bin/python -m playwright install-deps chromium
```

---

## 📜 Script

Create `capture_page.py`:

```python
#!/usr/bin/env python3
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://example.com"
SAVE_DIR = "/mnt/usb/screencap/output"

os.makedirs(SAVE_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_file = os.path.join(SAVE_DIR, f"capture_{timestamp}.png")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 2000})
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.screenshot(path=output_file, full_page=True)
    browser.close()

print(f"Saved: {output_file}")
```

---

## ⚙️ Configuration

Edit:

```python
URL = "https://example.com"
SAVE_DIR = "/mnt/usb/screencap/output"
```

---

## ▶️ Run

```bash
source venv/bin/activate
python capture_page.py
```

---

## ⏰ Automation (cron)

```bash
crontab -e
```

Add:

```cron
0 */5 * * * /mnt/usb/screencap/venv/bin/python /mnt/usb/screencap/capture_page.py >> /mnt/usb/screencap/capture.log 2>&1
```

---

## 🧪 Test Playwright

```bash
python -c "from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://example.com')
    print(page.title())
    browser.close()"
```

---

## 🐛 Troubleshooting

### playwright not found

```bash
python -m playwright ...
```

### Missing dependencies

```bash
sudo /mnt/usb/screencap/venv/bin/python -m playwright install-deps chromium
```

---

## 📁 Output Example

```
output/
├── capture_2026-03-29_00-00-00.png
├── capture_2026-03-29_05-00-00.png
```

---

## 🔧 Notes

- Works on headless servers (Raspberry Pi, NUC, etc.)
- Use cron instead of infinite loops
- Extendable for monitoring, alerts, or ML pipelines
