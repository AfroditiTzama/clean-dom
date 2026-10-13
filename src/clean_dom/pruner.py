from typing import Optional, Set
from bs4 import BeautifulSoup

class DOMCleaner:
    """A high-performance HTML DOM pruner and cleaner designed to reduce token usage 
    in Large Language Model (LLM) context windows and web agents.
    """

    def __init__(
        self,
        strip_tags: Optional[Set[str]] = None,
        allowed_attributes: Optional[Set[str]] = None
    ):
        """Initializes the DOMCleaner with custom or default pruner rules.

        Args:
            strip_tags (set, optional): Custom tags to remove. Defaults to common bloat tags.
            allowed_attributes (set, optional): Custom attributes to keep. Defaults to standard semantic attributes.
        """
        self.strip_tags = strip_tags or {
            "script", "style", "meta", "link", "noscript", 
            "iframe", "svg", "canvas", "footer", "nav"
        }
        self.allowed_attributes = allowed_attributes or {
            "id", "class", "href", "src", "alt", "title"
        }

    def clean(self, html_content: str) -> str:
        """Cleans and prunes the provided HTML string.

        Args:
            html_content (str): The raw HTML snapshot to clean.

        Returns:
            str: The sanitized and minified HTML string.
        """
        if not html_content or not html_content.strip():
            return ""

        soup = BeautifulSoup(html_content, "lxml")

        # Remove unwanted tags completely
        for tag in soup.find_all(True):
            if tag.name in self.strip_tags:
                tag.decompose()

        # Filter attributes for all remaining tags
        for tag in soup.find_all(True):
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr not in self.allowed_attributes:
                    del tag[attr]

        return str(soup)