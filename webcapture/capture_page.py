#!/usr/bin/env python3
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://example.com"
SAVE_DIR = "/mnt/usb/screencap/output"

os.makedirs(SAVE_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
outfile = os.path.join(SAVE_DIR, f"capture_{timestamp}.png")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 2200})
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.screenshot(path=outfile, full_page=True)
    browser.close()

print(f"Saved {outfile}")
