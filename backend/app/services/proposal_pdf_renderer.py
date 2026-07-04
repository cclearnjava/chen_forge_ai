"""Render approved proposal DTO to PDF bytes via Playwright Chromium.

Storage adapter saves PDFs locally so they survive process restarts during development.
"""

import os
import hashlib

STORAGE_DIR = os.environ.get("PROPOSAL_PDF_STORAGE", "/tmp/chenforge-proposals")


def _build_print_html(data: dict) -> str:
    md = data.get("markdown", "")
    customer = data.get("customer_name", "")
    title = data.get("opportunity_title", "")
    approved_at = data.get("approved_at", "")

    html_body = ""
    for line in md.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            html_body += f"<h1>{stripped[2:]}</h1>\n"
        elif stripped.startswith("## "):
            html_body += f"<h2>{stripped[3:]}</h2>\n"
        elif stripped.startswith("- "):
            html_body += f"<li>{stripped[2:]}</li>\n"
        elif stripped:
            html_body += f"<p>{stripped}</p>\n"
        else:
            html_body += "<br/>\n"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  @page {{
    size: A4 portrait;
    margin: 18mm 16mm;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
  }}
  .cover {{
    text-align: center;
    padding: 60px 0 40px 0;
    page-break-after: always;
  }}
  .cover h1 {{ font-size: 24pt; margin-bottom: 8px; color: #2563eb; }}
  .cover .subtitle {{ font-size: 16pt; color: #4b5563; margin-bottom: 40px; }}
  .cover .meta {{ font-size: 10pt; color: #6b7280; line-height: 2; }}
  .cover .meta strong {{ color: #374151; }}
  h1 {{ font-size: 16pt; color: #2563eb; margin-top: 24px; page-break-after: avoid; }}
  h2 {{ font-size: 13pt; color: #374151; margin-top: 18px; page-break-after: avoid; }}
  p {{ margin: 6px 0; }}
  li {{ margin: 3px 0 3px 18px; }}
  .footer {{
    position: fixed; bottom: 0; left: 0; right: 0;
    text-align: center; font-size: 8pt; color: #9ca3af;
    padding: 8px 0; border-top: 1px solid #e5e7eb;
  }}
</style>
</head>
<body>
<div class="cover">
  <h1>ChenForge AI</h1>
  <div class="subtitle">PoC Proposal</div>
  <div class="meta">
    <strong>客户：</strong>{customer}<br/>
    <strong>商机：</strong>{title}<br/>
    <strong>生成日期：</strong>{approved_at[:10] if approved_at else "N/A"}
  </div>
</div>
{html_body}
<div class="footer">ChenForge AI · AI Consulting Delivery OS · Confidential</div>
</body>
</html>"""


class ProposalPdfStorage:
    """Local filesystem storage for generated proposal PDFs."""

    def __init__(self, base_dir: str = STORAGE_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, data: dict) -> str:
        key = f"{data.get('opportunity_id', 'unknown')}-{data.get('decision_id', 'unknown')}"
        safe = hashlib.sha256(key.encode()).hexdigest()[:16]
        return os.path.join(self.base_dir, f"{safe}.pdf")

    def get(self, data: dict) -> bytes | None:
        path = self._path(data)
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        return None

    def save(self, data: dict, pdf_bytes: bytes) -> str:
        path = self._path(data)
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        return path


_storage = ProposalPdfStorage()


def render_approved_proposal_pdf(data: dict) -> bytes:
    """Render proposal DTO to PDF bytes via Playwright Chromium.

    Caches result to local storage. Raises RuntimeError if Playwright is unavailable.
    """
    cached = _storage.get(data)
    if cached:
        return cached

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install playwright && python -m playwright install chromium"
        )

    html = _build_print_html(data)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        pdf_bytes = page.pdf(format="A4", print_background=True)
        browser.close()

    _storage.save(data, pdf_bytes)
    return pdf_bytes
