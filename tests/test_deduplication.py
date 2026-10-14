from clean_dom import DOMCleaner

LONG_TEXT = "A repeated navigation section with enough visible text."


def test_deduplication_is_disabled_by_default():
    html = f"<main><section>{LONG_TEXT}</section><section>{LONG_TEXT}</section></main>"

    result = DOMCleaner().clean_with_report(html)

    assert result.cleaned_html.count("<section>") == 2
    assert result.stats.duplicate_sections_removed == 0
    assert result.stats.duplicate_chars_removed == 0


def test_enabled_dedup_preserves_exact_clean_output_when_no_match_exists():
    html = "<main><p>First paragraph with useful visible content.</p></main>"

    baseline = DOMCleaner().clean(html)
    result = DOMCleaner(deduplicate_repeated_sections=True).clean_with_report(html)

    assert result.cleaned_html == baseline
    assert result.stats.duplicate_sections_removed == 0
    assert result.stats.duplicate_chars_removed == 0


def test_identical_sibling_sections_keep_the_first_instance():
    first_text = "Repeated   section content with sufficient visible text."
    second_text = "Repeated section content with sufficient visible text."
    html = (
        f"<main><section>{first_text}</section><section>{second_text}</section></main>"
    )

    cleaner = DOMCleaner(deduplicate_repeated_sections=True)
    cleaned = cleaner.clean(html)
    result = cleaner.clean_with_report(html)

    assert cleaned.count("<section>") == 1
    assert first_text in cleaned
    assert result.stats.duplicate_sections_removed == 1
    assert result.stats.duplicate_chars_removed > 0


def test_different_visible_text_prevents_deduplication():
    html = (
        "<main><section>First repeated-length block of visible text.</section>"
        "<section>Second repeated-length block of visible text.</section></main>"
    )

    cleaned = DOMCleaner(deduplicate_repeated_sections=True).clean(html)

    assert cleaned.count("<section>") == 2


def test_different_link_destinations_prevent_deduplication():
    html = (
        '<main><section><a href="/product/1">Buy this featured product</a></section>'
        '<section><a href="/product/2">Buy this featured product</a></section></main>'
    )

    cleaned = DOMCleaner(deduplicate_repeated_sections=True).clean(html)

    assert cleaned.count("<section>") == 2
    assert 'href="/product/1"' in cleaned
    assert 'href="/product/2"' in cleaned


def test_different_form_actions_prevent_deduplication():
    html = (
        '<main><section><form action="/one">Subscribe to our newsletter now</form></section>'
        '<section><form action="/two">Subscribe to our newsletter now</form></section></main>'
    )

    cleaned = DOMCleaner(deduplicate_repeated_sections=True).clean(html)

    assert cleaned.count("<section>") == 2
    assert 'action="/one"' in cleaned
    assert 'action="/two"' in cleaned


def test_product_cards_with_different_text_and_hrefs_remain():
    html = (
        '<main><div class="card"><a href="/a">Product Alpha featured model</a></div>'
        '<div class="card"><a href="/b">Product Beta featured model</a></div></main>'
    )

    cleaned = DOMCleaner(deduplicate_repeated_sections=True).clean(html)

    assert cleaned.count('class="card"') == 2
    assert "Product Alpha" in cleaned
    assert "Product Beta" in cleaned


def test_identical_nav_clones_are_removed_when_preserved_by_configuration():
    nav = f'<nav aria-label="Main menu"><a href="/home">{LONG_TEXT}</a></nav>'
    html = f"<main>{nav}{nav}</main>"

    result = DOMCleaner(
        remove_tags=set(), deduplicate_repeated_sections=True
    ).clean_with_report(html)

    assert result.cleaned_html.count("<nav") == 1
    assert result.stats.duplicate_sections_removed == 1


def test_tiny_trivial_siblings_are_not_deduplicated():
    html = "<main><span>•</span><span>•</span><li>|</li><li>|</li></main>"

    cleaned = DOMCleaner(deduplicate_repeated_sections=True).clean(html)

    assert cleaned.count("<span>") == 2
    assert cleaned.count("<li>") == 2


def test_nested_duplicate_sections_are_removed():
    section = f"<section>{LONG_TEXT}</section>"
    html = f"<main><div>{section}{section}</div></main>"

    result = DOMCleaner(deduplicate_repeated_sections=True).clean_with_report(html)

    assert result.cleaned_html.count("<section>") == 1
    assert result.stats.duplicate_sections_removed == 1


def test_malformed_html_is_deduplicated_after_parsing():
    html = f"<main><section>{LONG_TEXT}</section><section>{LONG_TEXT}</section>"

    result = DOMCleaner(deduplicate_repeated_sections=True).clean_with_report(html)

    assert result.cleaned_html.count("<section>") == 1
    assert result.stats.duplicate_sections_removed == 1


def test_unicode_text_is_fingerprinted_deterministically():
    text = "Καλημέρα κόσμε, αυτό είναι επαναλαμβανόμενο περιεχόμενο."
    html = f"<main><section>{text}</section><section>{text}</section></main>"
    cleaner = DOMCleaner(deduplicate_repeated_sections=True)

    first = cleaner.clean(html)
    second = cleaner.clean(html)

    assert first == second
    assert first.count("<section>") == 1


def test_mapping_uses_only_surviving_nodes_and_sequential_ids():
    section = f'<section><a href="/same">{LONG_TEXT}</a></section>'
    html = f"<main>{section}{section}<button>Next</button></main>"

    result = DOMCleaner(deduplicate_repeated_sections=True).clean_with_mapping(html)

    assert result.cleaned_html.count("<section>") == 1
    assert list(result.element_map) == [1, 2]
    assert [item.tag for item in result.element_map.values()] == ["a", "button"]
    assert result.stats.duplicate_sections_removed == 1


def test_fingerprints_ignore_synthetic_mapping_ids():
    html = (
        '<main><section data-cdom-id="3">' + LONG_TEXT + "</section>"
        '<section data-cdom-id="8">' + LONG_TEXT + "</section></main>"
    )

    result = DOMCleaner(
        remove_tags=set(), deduplicate_repeated_sections=True
    ).clean_with_mapping(html)

    assert result.cleaned_html.count("<section") == 1
    assert result.stats.duplicate_sections_removed == 1


def test_clean_api_without_opt_in_remains_unchanged():
    html = f"<main><section>{LONG_TEXT}</section><section>{LONG_TEXT}</section></main>"

    assert DOMCleaner().clean(html) == DOMCleaner(
        deduplicate_repeated_sections=False
    ).clean(html)
