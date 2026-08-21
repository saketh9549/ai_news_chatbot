"""Full-text HTML and metadata extractor for news articles with OpenGraph image support."""

import logging
import re
from urllib.parse import urlparse
import httpx

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _extract_og_image(html: str) -> str | None:
    """Extract OpenGraph or Twitter preview image URL from HTML."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_img and og_img.get("content"):
            img_url = og_img.get("content").strip()
            if img_url.startswith("http"):
                return img_url
    except Exception:
        pass

    # Regex fallback
    match = re.search(r'<meta[^>]+(?:property=["\']og:image["\']|name=["\']twitter:image["\'])[^>]+content=["\'](https?://[^"\']+)["\']', html, re.I)
    if match:
        return match.group(1)
    return None


def _clean_html_text(html: str) -> str:
    """Extract clean text content from raw HTML without scripts, styles, or boilerplate."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Remove irrelevant elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript", "form", "svg"]):
            tag.decompose()

        # Prioritize main article content containers
        article_elem = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"article|content|story|body", re.I))
        target = article_elem if article_elem else soup.body or soup

        # Extract text from paragraphs within target
        paragraphs = target.find_all("p")
        if paragraphs and len(paragraphs) >= 2:
            text_blocks = [p.get_text(separator=" ", strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20]
            if text_blocks:
                return "\n\n".join(text_blocks)

        # Fallback to general text extraction
        return target.get_text(separator="\n\n", strip=True)
    except Exception as e:
        logger.debug("BeautifulSoup extraction fallback to regex: %s", e)
        # Regex fallback
        no_scripts = re.sub(r"<(script|style|nav|header|footer).*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        no_tags = re.sub(r"<[^>]+>", " ", no_scripts)
        clean = re.sub(r"\s+", " ", no_tags).strip()
        return clean


def extract_article_content(url: str, timeout: float = 10.0) -> str | None:
    """Fetch URL and extract clean article text."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=HEADERS) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None

            extracted = _clean_html_text(resp.text)
            if extracted and len(extracted.strip()) > 100:
                return extracted.strip()
    except Exception as e:
        logger.debug("Error extracting article text from %s: %s", url, e)
    return None


def extract_article_with_image(url: str, timeout: float = 10.0) -> tuple[str | None, str | None]:
    """Fetch URL and extract both clean article text and OpenGraph preview image."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=HEADERS) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None, None

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None, None

            text = _clean_html_text(resp.text)
            img = _extract_og_image(resp.text)
            return (text.strip() if text else None, img)
    except Exception as e:
        logger.debug("Error extracting article metadata from %s: %s", url, e)
    return None, None
