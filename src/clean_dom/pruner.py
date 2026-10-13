import warnings
from typing import Optional, Set

from bs4 import BeautifulSoup, Comment

DEFAULT_REMOVE_TAGS = {
    "script",
    "style",
    "meta",
    "link",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "footer",
    "nav",
}

DEFAULT_ALLOWED_ATTRIBUTES = {
    "id",
    "class",
    "href",
    "src",
    "alt",
    "title",
    "name",
    "type",
    "value",
    "placeholder",
    "role",
    "aria-label",
    "aria-labelledby",
    "for",
    "action",
    "method",
    "checked",
    "selected",
    "disabled",
    "required",
}


class DOMCleaner:
    """A lightweight HTML DOM cleaner for LLM and AI-agent pipelines.

    Removes unnecessary HTML elements and attributes while preserving
    useful DOM structure and semantic information.
    """

    def __init__(
        self,
        strip_tags: Optional[Set[str]] = None,
        allowed_attributes: Optional[Set[str]] = None,
        *,
        remove_tags: Optional[Set[str]] = None,
        additional_remove_tags: Optional[Set[str]] = None,
        unwrap_tags: Optional[Set[str]] = None,
        remove_comments: bool = True,
        max_attribute_length: Optional[int] = 500,
        drop_data_urls: bool = True,
    ):
        """
        Initialize the DOM cleaner.

        Args:
            remove_tags:
                Complete set of tags to remove. If None, default rules are used.

            additional_remove_tags:
                Extra tags to remove in addition to the defaults.

            unwrap_tags:
                Tags whose wrapper is removed while preserving their contents.

            allowed_attributes:
                Attributes to preserve.

            remove_comments:
                Remove HTML comments when True.

            max_attribute_length:
                Maximum length of an attribute value.
                Set to None to disable this limit.

            drop_data_urls:
                Remove data: URLs from href and src attributes.

            strip_tags:
                Deprecated alias for remove_tags.
        """

        # Backwards compatibility with clean-dom 0.1.x
        if strip_tags is not None:
            if remove_tags is not None:
                raise ValueError(
                    "Use either 'remove_tags' or deprecated 'strip_tags', "
                    "not both."
                )

            warnings.warn(
                "'strip_tags' is deprecated and will be removed in a future "
                "version. Use 'remove_tags' instead.",
                DeprecationWarning,
                stacklevel=2,
            )

            remove_tags = strip_tags

        self.remove_tags = (
            set(DEFAULT_REMOVE_TAGS)
            if remove_tags is None
            else set(remove_tags)
        )

        if additional_remove_tags:
            self.remove_tags.update(additional_remove_tags)

        self.unwrap_tags = set() if unwrap_tags is None else set(unwrap_tags)

        self.allowed_attributes = (
            set(DEFAULT_ALLOWED_ATTRIBUTES)
            if allowed_attributes is None
            else set(allowed_attributes)
        )

        self.remove_comments = remove_comments
        self.max_attribute_length = max_attribute_length
        self.drop_data_urls = drop_data_urls

    @property
    def strip_tags(self) -> Set[str]:
        """Deprecated alias for the active tag-removal set."""
        warnings.warn(
            "'strip_tags' is deprecated and will be removed in a future "
            "version. Use 'remove_tags' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.remove_tags

    @strip_tags.setter
    def strip_tags(self, tags: Set[str]) -> None:
        warnings.warn(
            "'strip_tags' is deprecated and will be removed in a future "
            "version. Use 'remove_tags' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.remove_tags = set(tags)

    def clean(self, html_content: str) -> str:
        """Clean and prune an HTML string."""

        if not html_content or not html_content.strip():
            return ""

        soup = BeautifulSoup(html_content, "lxml")

        # Remove HTML comments.
        if self.remove_comments:
            for comment in soup.find_all(
                string=lambda text: isinstance(text, Comment)
            ):
                comment.extract()

        # Remove elements, unwrap unnecessary wrappers,
        # and clean attributes.
        for tag in list(soup.find_all(True)):
            if tag.name in self.remove_tags:
                tag.decompose()
                continue

            if tag.name in self.unwrap_tags:
                tag.unwrap()
                continue

            cleaned_attributes = {}

            for attr, value in tag.attrs.items():
                if attr not in self.allowed_attributes:
                    continue

                if isinstance(value, list):
                    value = " ".join(str(item) for item in value)

                value = str(value)

                if (
                    self.drop_data_urls
                    and attr in {"src", "href"}
                    and value.lower().startswith("data:")
                ):
                    continue

                if (
                    self.max_attribute_length is not None
                    and len(value) > self.max_attribute_length
                ):
                    continue

                cleaned_attributes[attr] = value

            tag.attrs = cleaned_attributes

        return str(soup)

    @classmethod
    def preset(cls, name: str) -> "DOMCleaner":
        """Create a cleaner using a predefined strategy."""

        if name == "minimal":
            return cls(
                allowed_attributes={"id", "href"},
            )

        if name == "content":
            return cls(
                additional_remove_tags={"aside"},
                unwrap_tags={"span"},
            )

        if name == "agent":
            return cls(
                unwrap_tags={"span"},
                allowed_attributes={
                    "id",
                    "class",
                    "href",
                    "src",
                    "alt",
                    "title",
                    "name",
                    "type",
                    "value",
                    "placeholder",
                    "role",
                    "aria-label",
                    "aria-labelledby",
                    "for",
                    "action",
                    "method",
                    "checked",
                    "selected",
                    "disabled",
                    "required",
                },
            )

        raise ValueError(
            f"Unknown preset: {name!r}. "
            "Available presets: 'minimal', 'content', 'agent'."
        )