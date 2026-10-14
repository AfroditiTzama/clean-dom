import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import Tag

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.semantics import (
    evaluate_semantic_retention,
    expectations_for_variant,
)
from clean_dom import DOMCleaner

FIXTURE_DIR = PROJECT_ROOT / "benchmarks" / "fixtures"
MANIFEST_PATH = PROJECT_ROOT / "benchmarks" / "fixtures.json"
MINIMUM_FIXTURE_BYTES = 700


def _load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for hidden in soup.find_all(["script", "style", "noscript"]):
        hidden.decompose()
    return " ".join(soup.stripped_strings)


def _attribute_text(tag: Tag, name: str) -> str:
    value = tag.attrs.get(name)
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(part) for part in value)
    return str(value)


def test_every_manifest_entry_has_fixture_metadata_and_file():
    manifest = _load_manifest()
    assert len(manifest) >= 6

    for entry in manifest:
        fixture_path = FIXTURE_DIR / entry["filename"]
        assert fixture_path.is_file(), entry["filename"]
        assert entry["category"]
        assert entry["source_type"] == "synthetic-realistic"
        assert entry["purpose"]
        assert entry["patterns"]
        assert isinstance(entry["contains_exact_duplicates"], bool)
        assert isinstance(entry["contains_interactive_elements"], bool)
        assert isinstance(entry["contains_repeated_distinct_items"], bool)


def test_fixtures_have_meaningful_content_and_balanced_noise():
    for entry in _load_manifest():
        html = (FIXTURE_DIR / entry["filename"]).read_text(encoding="utf-8")
        assert len(html.encode("utf-8")) >= MINIMUM_FIXTURE_BYTES

        visible_text = _visible_text(html)
        assert len(visible_text) >= 300, entry["filename"]
        assert len(visible_text) / len(html) >= 0.12, entry["filename"]

        soup = BeautifulSoup(html, "lxml")
        executable_or_style_chars = sum(
            len(tag.get_text()) for tag in soup.find_all(["script", "style"])
        )
        assert executable_or_style_chars / len(html) <= 0.8, entry["filename"]
        assert not re.search(r"data:[^\s\"']{1000,}", html, flags=re.IGNORECASE)
        assert (
            max(
                (len(tag.get_text()) for tag in soup.find_all(["script", "style"])),
                default=0,
            )
            < 10_000
        )


def test_ecommerce_fixture_has_distinct_products_and_destinations():
    html = (FIXTURE_DIR / "ecommerce.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(".product-card")
    product_links = [card.select_one("h2 a") for card in cards]
    hrefs = [_attribute_text(link, "href") for link in product_links if link]
    names = [link.get_text(" ", strip=True) for link in product_links if link]

    assert len(cards) >= 3
    assert len(set(hrefs)) == len(hrefs)
    assert len(set(names)) == len(names)
    assert all(card.find("form") and card.find("button") for card in cards)
    assert all(card.find("img", alt=True) for card in cards)
    assert any("data-track" in card.attrs for card in cards)
    assert max(len(_attribute_text(card, "class").split()) for card in cards) >= 5


def test_navigation_fixture_has_exact_and_distinct_sibling_patterns():
    html = (FIXTURE_DIR / "navigation_heavy.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main")
    assert main is not None
    sibling_sections = main.find_all("section", recursive=False)
    normalized = [section.decode(formatter="minimal") for section in sibling_sections]
    assert len(normalized) != len(set(normalized))

    links = soup.find_all("a", href=True)
    assert len({_attribute_text(link, "href") for link in links}) >= 8
    assert any(
        "desktop" in _attribute_text(section, "class") for section in sibling_sections
    )
    assert any(
        "mobile" in _attribute_text(section, "class") for section in sibling_sections
    )


def test_agent_oriented_fixtures_have_accessible_or_form_controls():
    for filename in ("ecommerce.html", "react_app.html"):
        soup = BeautifulSoup(
            (FIXTURE_DIR / filename).read_text(encoding="utf-8"), "lxml"
        )
        assert soup.select_one("[role], [aria-label]")
        assert soup.find("form")
        assert soup.find("input")


def test_manifest_duplicate_claim_matches_navigation_fixture():
    entries = {entry["filename"]: entry for entry in _load_manifest()}
    assert entries["navigation_heavy.html"]["contains_exact_duplicates"] is True
    assert entries["ecommerce.html"]["contains_exact_duplicates"] is False
    assert entries["ecommerce.html"]["contains_repeated_distinct_items"] is True


def test_deduplication_preserves_distinct_fixture_products():
    html = (FIXTURE_DIR / "ecommerce.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    expected_hrefs = {
        _attribute_text(link, "href")
        for link in soup.select(".product-card h2 a[href]")
    }

    result = DOMCleaner(deduplicate_repeated_sections=True).clean_with_report(html)
    cleaned = BeautifulSoup(result.cleaned_html, "lxml")

    assert len(cleaned.select(".product-card")) == len(expected_hrefs)
    assert expected_hrefs <= {
        _attribute_text(link, "href") for link in cleaned.find_all("a", href=True)
    }


def test_deduplication_removes_one_exact_navigation_copy_only():
    html = (FIXTURE_DIR / "navigation_heavy.html").read_text(encoding="utf-8")
    default_cleaned = BeautifulSoup(DOMCleaner().clean(html), "lxml")
    expected_hrefs = {
        _attribute_text(link, "href")
        for link in BeautifulSoup(html, "lxml").find_all("a", href=True)
    }

    result = DOMCleaner(
        remove_tags=set(), deduplicate_repeated_sections=True
    ).clean_with_report(html)
    cleaned = BeautifulSoup(result.cleaned_html, "lxml")

    assert result.stats.duplicate_sections_removed == 1
    assert len(default_cleaned.select("main > section.menu-copy")) == 2
    assert len(cleaned.select("main > section.menu-copy")) == 1
    assert expected_hrefs <= {
        _attribute_text(link, "href") for link in cleaned.find_all("a", href=True)
    }


def test_all_declared_required_semantics_survive_their_selected_variants():
    variants = {
        "default": DOMCleaner,
        "agent": lambda: DOMCleaner.preset("agent"),
        "deduplication": lambda: DOMCleaner(deduplicate_repeated_sections=True),
    }
    for fixture in _load_manifest():
        html = (FIXTURE_DIR / fixture["filename"]).read_text(encoding="utf-8")
        for variant, cleaner_factory in variants.items():
            cleaner = cleaner_factory()
            cleaned = cleaner.clean(html)
            expectations = expectations_for_variant(fixture, variant)
            retention = evaluate_semantic_retention(cleaned, expectations)
            assert retention["semantic_retention_percent"] == 100.0, (
                fixture["filename"],
                variant,
                retention["missing_semantics"],
                expectations.get("notes"),
            )


def test_default_and_agent_navigation_link_behavior_is_explicit():
    html = (FIXTURE_DIR / "navigation_heavy.html").read_text(encoding="utf-8")
    default_html = DOMCleaner().clean(html)
    agent_html = DOMCleaner.preset("agent").clean(html)

    assert "/housing" not in default_html
    assert 'href="/housing"' in agent_html
    assert 'href="/housing/apply"' in agent_html


def test_default_and_agent_breadcrumb_behavior_is_explicit():
    html = (FIXTURE_DIR / "docs.html").read_text(encoding="utf-8")
    default_html = DOMCleaner().clean(html)
    agent_html = DOMCleaner.preset("agent").clean(html)

    assert 'href="/guides/imports"' not in default_html
    assert 'href="/guides/imports"' in agent_html


def test_default_and_agent_pagination_behavior_is_explicit():
    html = (FIXTURE_DIR / "ecommerce.html").read_text(encoding="utf-8")
    default_html = DOMCleaner().clean(html)
    agent_html = DOMCleaner.preset("agent").clean(html)

    assert 'href="?page=1"' not in default_html
    assert 'href="?page=1"' in agent_html
    assert 'href="?page=2"' in agent_html


def test_default_and_agent_footer_behavior_is_explicit():
    html = (FIXTURE_DIR / "news.html").read_text(encoding="utf-8")
    default_html = DOMCleaner().clean(html)
    agent_html = DOMCleaner.preset("agent").clean(html)

    assert 'href="/privacy"' not in default_html
    assert 'href="/privacy"' in agent_html


def test_semantic_retention_uses_exact_normalized_text_and_attributes():
    metrics = evaluate_semantic_retention(
        '<main><p>Alpha   beta</p><a href="/exact">Open</a>'
        '<input aria-label="Search items"></main>',
        {
            "must_preserve_text": ["Alpha beta", "alpha beta"],
            "must_preserve_hrefs": ["/exact"],
            "must_preserve_attributes": [
                {"tag": "input", "attribute": "aria-label", "value": "Search items"}
            ],
        },
    )

    assert metrics["required_text_total"] == 2
    assert metrics["required_text_preserved"] == 1
    assert metrics["required_href_total"] == 1
    assert metrics["required_href_preserved"] == 1
    assert metrics["required_attributes_total"] == 1
    assert metrics["required_attributes_preserved"] == 1
    assert metrics["semantic_retention_percent"] == 75.0
    assert metrics["missing_semantics"] == ["text: 'alpha beta'"]
