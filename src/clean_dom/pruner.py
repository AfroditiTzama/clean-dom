import json
import warnings
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping, Optional, Set, Tuple, Union

from bs4 import BeautifulSoup, Comment
from bs4.element import Tag

from ._tokenizers import Tokenizer, count_tokens

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

_MAX_ELEMENT_TEXT_LENGTH = 240
_MAX_ELEMENT_ATTRIBUTE_LENGTH = 500
_ACTIONABLE_TAGS = {
    "a",
    "button",
    "details",
    "form",
    "iframe",
    "input",
    "label",
    "option",
    "select",
    "summary",
    "textarea",
}
_MAPPING_ATTRIBUTES = {"aria-label", "href", "role", "tabindex"}
_MIN_DUPLICATE_TEXT_LENGTH = 24
_MIN_DUPLICATE_SUBTREE_TAGS = 4
_MIN_DUPLICATE_SERIALIZED_LENGTH = 120


@dataclass(frozen=True)
class ElementInfo:
    """Bounded metadata for a useful element in the cleaned HTML."""

    cdom_id: int
    tag: str
    text: str
    html_id: Optional[str]
    classes: Tuple[str, ...]
    href: Optional[str]
    name: Optional[str]
    type: Optional[str]
    role: Optional[str]
    aria_label: Optional[str]


@dataclass(frozen=True)
class CleaningStats:
    """Character and optional token counts for a cleaning operation."""

    input_chars: int
    output_chars: int
    chars_saved: int
    char_reduction_percent: float
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    tokens_saved: Optional[int]
    token_reduction_percent: Optional[float]
    max_tokens: Optional[int] = None
    budget_met: Optional[bool] = None
    strategy_level: Optional[int] = None
    duplicate_sections_removed: int = 0
    duplicate_chars_removed: int = 0


@dataclass(frozen=True)
class CleaningResult:
    """The cleaned HTML and immutable metrics describing the operation."""

    cleaned_html: str
    stats: CleaningStats
    element_map: Mapping[int, ElementInfo] = field(
        default_factory=lambda: MappingProxyType({})
    )


def _reduction_percent(total: int, saved: int) -> float:
    """Return the percentage reduction, using zero for empty input."""
    if total == 0:
        return 0.0
    return saved / total * 100


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
        deduplicate_repeated_sections: bool = False,
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

            deduplicate_repeated_sections:
                Remove conservative, substantially identical sibling subtrees.
                Disabled by default.

            strip_tags:
                Deprecated alias for remove_tags.
        """

        # Backwards compatibility with clean-dom 0.1.x
        if strip_tags is not None:
            if remove_tags is not None:
                raise ValueError(
                    "Use either 'remove_tags' or deprecated 'strip_tags', not both."
                )

            warnings.warn(
                "'strip_tags' is deprecated and will be removed in a future "
                "version. Use 'remove_tags' instead.",
                DeprecationWarning,
                stacklevel=2,
            )

            remove_tags = strip_tags

        self.remove_tags = (
            set(DEFAULT_REMOVE_TAGS) if remove_tags is None else set(remove_tags)
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
        self.deduplicate_repeated_sections = deduplicate_repeated_sections

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

        cleaned_html, _, _ = self._clean_html_with_stats(html_content)
        return cleaned_html

    def _clean_html_with_stats(self, html_content: str) -> Tuple[str, int, int]:
        """Clean HTML and return duplicate section and character counts."""

        if not html_content or not html_content.strip():
            return "", 0, 0

        soup = BeautifulSoup(html_content, "lxml")

        # Remove HTML comments.
        if self.remove_comments:
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

        # Remove elements, unwrap unnecessary wrappers,
        # and clean attributes.
        for tag in list(soup.find_all(True)):
            # A removed ancestor may have decomposed this descendant earlier
            # in the traversal, clearing its attributes.
            if tag.attrs is None:
                continue

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

        cleaned_html = str(soup)
        if not self.deduplicate_repeated_sections:
            return cleaned_html, 0, 0
        return self._deduplicate_sibling_sections(cleaned_html)

    def clean_with_report(
        self,
        html_content: str,
        tokenizer: Optional[Union[str, Tokenizer]] = None,
    ) -> CleaningResult:
        """Clean HTML and return character metrics plus optional token metrics.

        Pass ``tokenizer="tiktoken"`` to use the optional ``cl100k_base``
        encoding, or pass an object with an ``encode(text)`` method.
        """
        cleaned_html, duplicate_count, duplicate_chars = self._clean_html_with_stats(
            html_content
        )
        return self._make_cleaning_result(
            html_content,
            cleaned_html,
            tokenizer,
            duplicate_sections_removed=duplicate_count,
            duplicate_chars_removed=duplicate_chars,
        )

    def clean_with_mapping(
        self,
        html_content: str,
        add_element_ids: bool = True,
    ) -> CleaningResult:
        """Clean HTML and return metadata for useful elements in the result.

        Mapping keys are integer ``data-cdom-id`` values starting at 1. The
        IDs follow cleaned DOM traversal order and do not replace native HTML
        ``id`` attributes.
        """
        if not add_element_ids:
            cleaned_html, duplicate_count, duplicate_chars = (
                self._clean_html_with_stats(html_content)
            )
            return CleaningResult(
                cleaned_html=cleaned_html,
                stats=self._make_cleaning_result(
                    html_content,
                    cleaned_html,
                    None,
                    duplicate_sections_removed=duplicate_count,
                    duplicate_chars_removed=duplicate_chars,
                ).stats,
            )

        allowed_attributes = set(self.allowed_attributes)
        allowed_attributes.add("tabindex")
        allowed_attributes.discard("data-cdom-id")
        mapping_cleaner = DOMCleaner(
            remove_tags=set(self.remove_tags),
            allowed_attributes=allowed_attributes,
            unwrap_tags=set(self.unwrap_tags),
            remove_comments=self.remove_comments,
            max_attribute_length=self.max_attribute_length,
            drop_data_urls=self.drop_data_urls,
            deduplicate_repeated_sections=self.deduplicate_repeated_sections,
        )
        cleaned_html, duplicate_count, duplicate_chars = (
            mapping_cleaner._clean_html_with_stats(html_content)
        )
        cleaned_html, element_map = self._add_element_ids(cleaned_html)
        stats = self._make_cleaning_result(
            html_content,
            cleaned_html,
            None,
            duplicate_sections_removed=duplicate_count,
            duplicate_chars_removed=duplicate_chars,
        ).stats

        return CleaningResult(
            cleaned_html=cleaned_html,
            stats=stats,
            element_map=element_map,
        )

    @staticmethod
    def _add_element_ids(
        cleaned_html: str,
    ) -> Tuple[str, Mapping[int, ElementInfo]]:
        """Assign deterministic IDs to useful elements in cleaned DOM order."""
        if not cleaned_html:
            return "", MappingProxyType({})

        soup = BeautifulSoup(cleaned_html, "lxml")
        element_map = {}
        next_id = 1

        for tag in soup.find_all(True):
            if tag.name not in _ACTIONABLE_TAGS and not any(
                attribute in tag.attrs for attribute in _MAPPING_ATTRIBUTES
            ):
                continue

            tag["data-cdom-id"] = str(next_id)
            element_map[next_id] = ElementInfo(
                cdom_id=next_id,
                tag=str(tag.name),
                text=DOMCleaner._bounded_element_text(tag),
                html_id=DOMCleaner._bounded_attribute(tag.get("id")),
                classes=DOMCleaner._element_classes(tag),
                href=DOMCleaner._bounded_attribute(tag.get("href")),
                name=DOMCleaner._bounded_attribute(tag.get("name")),
                type=DOMCleaner._bounded_attribute(tag.get("type")),
                role=DOMCleaner._bounded_attribute(tag.get("role")),
                aria_label=DOMCleaner._bounded_attribute(tag.get("aria-label")),
            )
            next_id += 1

        return str(soup), MappingProxyType(element_map)

    @staticmethod
    def _bounded_element_text(tag: Tag) -> str:
        """Normalize descendant text and cap its stored length."""
        text = " ".join(" ".join(part.split()) for part in tag.stripped_strings)
        if len(text) > _MAX_ELEMENT_TEXT_LENGTH:
            return text[: _MAX_ELEMENT_TEXT_LENGTH - 1].rstrip() + "…"
        return text

    @staticmethod
    def _bounded_attribute(value: object) -> Optional[str]:
        """Convert and cap an attribute value before storing it in the map."""
        if value is None:
            return None
        if isinstance(value, list):
            value = " ".join(str(item) for item in value)
        text = str(value)
        if len(text) > _MAX_ELEMENT_ATTRIBUTE_LENGTH:
            return text[: _MAX_ELEMENT_ATTRIBUTE_LENGTH - 1] + "…"
        return text

    @staticmethod
    def _element_classes(tag: Tag) -> Tuple[str, ...]:
        """Return a bounded tuple of class names from an element."""
        classes = tag.get("class")
        if classes is None:
            return ()
        if isinstance(classes, str):
            classes = classes.split()
        return tuple(
            DOMCleaner._bounded_attribute(class_name) or ""
            for class_name in classes[:20]
        )

    @staticmethod
    def _deduplicate_sibling_sections(html_content: str) -> Tuple[str, int, int]:
        """Remove later equivalent sibling subtrees using stable fingerprints.

        A candidate must contain at least 24 normalized visible-text
        characters, or at least four tags and 120 serialized characters.
        Fingerprints include the complete cleaned structure and attributes,
        except clean-dom's synthetic mapping ID.
        """
        if not html_content:
            return "", 0, 0

        soup = BeautifulSoup(html_content, "lxml")
        removed_count = 0
        removed_chars = 0

        def fingerprint(tag: Tag) -> Tuple[str, int, int]:
            normalized_text_parts = []

            def encode_node(node: object) -> object:
                if isinstance(node, Tag):
                    attrs = []
                    for name, value in sorted(node.attrs.items()):
                        if name == "data-cdom-id":
                            continue
                        if isinstance(value, list):
                            value = " ".join(str(part) for part in value)
                        attrs.append((name, " ".join(str(value).split())))
                    children = [encode_node(child) for child in node.children]
                    return [str(node.name), attrs, children]

                text = " ".join(str(node).split())
                if text:
                    normalized_text_parts.append(text)
                return text

            encoded = encode_node(tag)
            normalized_text = " ".join(normalized_text_parts)
            tag_count = len(tag.find_all(True)) + 1
            fingerprint_text = json.dumps(
                encoded, ensure_ascii=False, separators=(",", ":")
            )
            return fingerprint_text, len(normalized_text), tag_count

        def prune_children(parent: Tag) -> None:
            nonlocal removed_count, removed_chars
            seen_fingerprints = set()
            for child in list(parent.find_all(recursive=False)):
                serialized = str(child)
                key, text_length, tag_count = fingerprint(child)
                if text_length < _MIN_DUPLICATE_TEXT_LENGTH and not (
                    tag_count >= _MIN_DUPLICATE_SUBTREE_TAGS
                    and len(serialized) >= _MIN_DUPLICATE_SERIALIZED_LENGTH
                ):
                    seen_fingerprints.add(key)
                    prune_children(child)
                    continue

                if key in seen_fingerprints:
                    removed_chars += len(serialized)
                    removed_count += 1
                    child.decompose()
                    continue

                seen_fingerprints.add(key)
                prune_children(child)

        for root in soup.find_all(recursive=False):
            prune_children(root)

        # Preserve the cleaner's exact serialization when no duplicate was
        # removed; reparsing alone must not appear as a reduction.
        return (
            str(soup) if removed_count else html_content,
            removed_count,
            removed_chars,
        )

    def clean_to_budget(
        self,
        html_content: str,
        max_tokens: int,
        tokenizer: str = "tiktoken",
    ) -> CleaningResult:
        """Progressively clean HTML until it fits a token budget or no level fits.

        Each strategy starts from the original input and uses an independent
        cleaner, so this method never changes this instance's configuration.
        If no strategy meets the budget, return the candidate with the fewest
        tokens and set ``stats.budget_met`` to ``False``.
        """
        if (
            isinstance(max_tokens, bool)
            or not isinstance(max_tokens, int)
            or max_tokens <= 0
        ):
            raise ValueError("max_tokens must be a positive integer.")

        best_result = None
        best_level = 0

        for strategy_level in range(5):
            candidate = self._clean_for_budget_level(
                html_content,
                strategy_level,
                tokenizer,
            )
            output_tokens = candidate.stats.output_tokens
            assert output_tokens is not None

            if best_result is None:
                best_result = candidate
                best_level = strategy_level
            else:
                best_output_tokens = best_result.stats.output_tokens
                assert best_output_tokens is not None
                if (output_tokens, candidate.stats.output_chars) < (
                    best_output_tokens,
                    best_result.stats.output_chars,
                ):
                    best_result = candidate
                    best_level = strategy_level

            if output_tokens <= max_tokens:
                best_result = candidate
                best_level = strategy_level
                break

        assert best_result is not None
        output_tokens = best_result.stats.output_tokens
        assert output_tokens is not None
        stats = replace(
            best_result.stats,
            max_tokens=max_tokens,
            budget_met=output_tokens <= max_tokens,
            strategy_level=best_level,
        )
        return CleaningResult(cleaned_html=best_result.cleaned_html, stats=stats)

    def _clean_for_budget_level(
        self,
        html_content: str,
        strategy_level: int,
        tokenizer: str,
    ) -> CleaningResult:
        """Create and run one isolated progressive cleaning strategy."""
        if strategy_level == 0:
            return self.clean_with_report(html_content, tokenizer=tokenizer)

        remove_tags = set(self.remove_tags)
        unwrap_tags = set(self.unwrap_tags)
        max_attribute_length = self.max_attribute_length

        if max_attribute_length is None:
            max_attribute_length = 500

        if strategy_level >= 2:
            remove_tags.update({"aside", "header", "footer", "nav"})

        cleaner = DOMCleaner(
            remove_tags=remove_tags,
            allowed_attributes=set(self.allowed_attributes),
            unwrap_tags=unwrap_tags,
            remove_comments=True,
            max_attribute_length=max_attribute_length,
            drop_data_urls=True,
            deduplicate_repeated_sections=self.deduplicate_repeated_sections,
        )
        cleaned_html, duplicate_count, duplicate_chars = cleaner._clean_html_with_stats(
            html_content
        )

        if strategy_level >= 3:
            cleaned_html = self._unwrap_safe_wrappers(cleaned_html)

        if strategy_level >= 4:
            cleaned_html = self._collapse_redundant_dom(cleaned_html)

        return self._make_cleaning_result(
            html_content,
            cleaned_html,
            tokenizer,
            duplicate_sections_removed=duplicate_count,
            duplicate_chars_removed=duplicate_chars,
        )

    @staticmethod
    def _collapse_redundant_dom(html_content: str) -> str:
        """Remove empty neutral containers and unwrap attribute-free wrappers."""
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "lxml")
        empty_container_tags = {
            "article",
            "blockquote",
            "div",
            "figcaption",
            "figure",
            "li",
            "ol",
            "p",
            "section",
            "ul",
        }
        wrapper_tags = {"div", "font", "span"}

        for tag in reversed(list(soup.find_all(True))):
            if (
                tag.name in empty_container_tags
                and not tag.get_text(strip=True)
                and not tag.find(True)
                and not tag.attrs
            ):
                tag.decompose()

        for tag in reversed(list(soup.find_all(True))):
            if tag.name in wrapper_tags and not tag.attrs:
                tag.unwrap()

        return str(soup)

    @staticmethod
    def _unwrap_safe_wrappers(html_content: str) -> str:
        """Unwrap attribute-free span and font elements while preserving contents."""
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "lxml")
        for tag in reversed(list(soup.find_all(["span", "font"]))):
            if not tag.attrs:
                tag.unwrap()
        return str(soup)

    @staticmethod
    def _make_cleaning_result(
        input_html: str,
        cleaned_html: str,
        tokenizer: Optional[Union[str, Tokenizer]],
        *,
        duplicate_sections_removed: int = 0,
        duplicate_chars_removed: int = 0,
    ) -> CleaningResult:
        """Create a complete cleaning report for a specific output string."""
        input_chars = len(input_html)
        output_chars = len(cleaned_html)
        chars_saved = input_chars - output_chars

        if tokenizer is None:
            input_tokens = output_tokens = tokens_saved = token_reduction_percent = None
        else:
            input_tokens = count_tokens(input_html, tokenizer)
            output_tokens = count_tokens(cleaned_html, tokenizer)
            tokens_saved = input_tokens - output_tokens
            token_reduction_percent = _reduction_percent(input_tokens, tokens_saved)

        return CleaningResult(
            cleaned_html=cleaned_html,
            stats=CleaningStats(
                input_chars=input_chars,
                output_chars=output_chars,
                chars_saved=chars_saved,
                char_reduction_percent=_reduction_percent(input_chars, chars_saved),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                tokens_saved=tokens_saved,
                token_reduction_percent=token_reduction_percent,
                duplicate_sections_removed=duplicate_sections_removed,
                duplicate_chars_removed=duplicate_chars_removed,
            ),
        )

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
                # Preserve navigation and footer links for agent workflows.
                # The general-purpose cleaner keeps its historical removals.
                remove_tags=DEFAULT_REMOVE_TAGS - {"nav", "footer"},
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
