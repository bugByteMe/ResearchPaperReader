from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import fitz
import httpx

from app.config import settings

ALLOWED_PDF_HOSTS = {"arxiv.org", "export.arxiv.org"}


def fetch_pdf_text(pdf_url: str) -> str:
    if urlparse(pdf_url).hostname not in ALLOWED_PDF_HOSTS:
        raise ValueError("PDF URL host is not allowed")
    with TemporaryDirectory() as tmpdir:
        pdf_path = f"{tmpdir}/paper.pdf"
        with httpx.stream("GET", pdf_url, follow_redirects=True, timeout=settings.external_timeout_seconds) as response:
            response.raise_for_status()
            if urlparse(str(response.url)).hostname not in ALLOWED_PDF_HOSTS:
                raise ValueError("PDF redirect host is not allowed")
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type:
                raise ValueError("Remote response is not a PDF")
            total = 0
            with open(pdf_path, "wb") as pdf_file:
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > settings.pdf_max_bytes:
                        raise ValueError("PDF exceeds configured size limit")
                    pdf_file.write(chunk)

        text_parts: list[str] = []
        with fitz.open(pdf_path) as doc:
            if doc.page_count > settings.pdf_max_pages:
                raise ValueError("PDF exceeds configured page limit")
            for page in doc:
                text_parts.append(page.get_text())
        return "\n".join(text_parts).strip()
