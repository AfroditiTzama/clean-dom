"""Exact, deterministic semantic checks for benchmark cleaner outputs."""

from __future__ import annotations

import re
from typing import Any, Mapping

from bs4 import BeautifulSoup
from bs4.element import Tag


def normalize_text(value: str) -> str:
    """Collapse whitespace without changing case, punctuation, or wording."""
    return re.sub(r"\s+", " ", value).strip()


def expectations_for_variant(
    fixture: Mapping[str, Any], variant: str
) -> dict[str, Any]:
    """Combine fixture-wide requirements with optional variant requirements."""
    expectation_keys = (
        "must_preserve_text",
        "must_preserve_hrefs",
        "must_preserve_attributes",
        "optional_preserve_text",
        "optional_preserve_hrefs",
    )
    result = {key: list(fixture.get(key, [])) for key in expectation_keys}
    override = fixture.get("variant_expectations", {}).get(variant, {})
    for key in expectation_keys:
        result[key].extend(override.get(key, []))
    result["notes"] = override.get("notes", fixture.get("notes", ""))
    return result


def _attribute_value(tag: Tag, attribute: str) -> str:
    value = tag.attrs.get(attribute)
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(part) for part in value)
    return str(value)


def evaluate_semantic_retention(
    html: str, expectations: Mapping[str, Any]
) -> dict[str, Any]:
    """Measure exact required and optional text, href, and attribute retention."""
    soup = BeautifulSoup(html, "lxml")
    for hidden in soup.find_all(["script", "style", "noscript"]):
        hidden.decompose()
    visible_text = normalize_text(soup.get_text(" "))
    hrefs = {_attribute_value(tag, "href") for tag in soup.find_all(href=True)}

    required_text = [
        normalize_text(value) for value in expectations.get("must_preserve_text", [])
    ]
    preserved_text = [value for value in required_text if value in visible_text]

    required_hrefs = list(expectations.get("must_preserve_hrefs", []))
    preserved_hrefs = [value for value in required_hrefs if value in hrefs]

    required_attributes = list(expectations.get("must_preserve_attributes", []))
    preserved_attributes: list[Mapping[str, str]] = []
    for requirement in required_attributes:
        tag_name = requirement.get("tag")
        attribute = requirement["attribute"]
        value = requirement["value"]
        matching_tags = soup.find_all(tag_name) if tag_name else soup.find_all(True)
        if any(_attribute_value(tag, attribute) == value for tag in matching_tags):
            preserved_attributes.append(requirement)

    total = len(required_text) + len(required_hrefs) + len(required_attributes)
    preserved = len(preserved_text) + len(preserved_hrefs) + len(preserved_attributes)
    missing: list[str] = []
    missing.extend(
        f"text: {value!r}" for value in required_text if value not in preserved_text
    )
    missing.extend(
        f"href: {value!r}" for value in required_hrefs if value not in preserved_hrefs
    )
    missing.extend(
        "attribute: {tag}[{attribute}]={value!r}".format(**requirement)
        for requirement in required_attributes
        if requirement not in preserved_attributes
    )

    optional_text = [
        normalize_text(value)
        for value in expectations.get("optional_preserve_text", [])
    ]
    optional_hrefs = list(expectations.get("optional_preserve_hrefs", []))
    return {
        "required_text_total": len(required_text),
        "required_text_preserved": len(preserved_text),
        "required_href_total": len(required_hrefs),
        "required_href_preserved": len(preserved_hrefs),
        "required_attributes_total": len(required_attributes),
        "required_attributes_preserved": len(preserved_attributes),
        "semantic_retention_percent": preserved / total * 100 if total else 100.0,
        "optional_text_total": len(optional_text),
        "optional_text_preserved": sum(
            value in visible_text for value in optional_text
        ),
        "optional_href_total": len(optional_hrefs),
        "optional_href_preserved": sum(value in hrefs for value in optional_hrefs),
        "missing_semantics": missing,
    }
