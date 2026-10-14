from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from clean_dom import DOMCleaner, ElementInfo


def test_mapping_is_disabled_for_existing_clean_apis_by_default():
    html = '<a href="/pricing">Pricing</a>'
    cleaner = DOMCleaner()

    clean_html = cleaner.clean(html)
    report = cleaner.clean_with_report(html)
    mapping_disabled = cleaner.clean_with_mapping(html, add_element_ids=False)

    assert "data-cdom-id" not in clean_html
    assert "data-cdom-id" not in report.cleaned_html
    assert report.element_map == {}
    assert mapping_disabled.cleaned_html == clean_html
    assert mapping_disabled.element_map == {}


def test_links_receive_ids_and_element_metadata():
    result = DOMCleaner().clean_with_mapping('<a href="/pricing">Pricing</a>')

    assert '<a data-cdom-id="1" href="/pricing">Pricing</a>' in result.cleaned_html
    assert result.element_map[1] == ElementInfo(
        cdom_id=1,
        tag="a",
        text="Pricing",
        html_id=None,
        classes=(),
        href="/pricing",
        name=None,
        type=None,
        role=None,
        aria_label=None,
    )


def test_buttons_receive_ids():
    result = DOMCleaner().clean_with_mapping("<button>Start</button>")

    assert 'data-cdom-id="1"' in result.cleaned_html
    assert result.element_map[1].tag == "button"
    assert result.element_map[1].text == "Start"


def test_form_controls_receive_ids():
    html = '<form><input name="email"><select><option>Basic</option></select><textarea>Notes</textarea></form>'

    result = DOMCleaner().clean_with_mapping(html)

    assert [info.tag for info in result.element_map.values()] == [
        "form",
        "input",
        "select",
        "option",
        "textarea",
    ]
    assert [info.cdom_id for info in result.element_map.values()] == [1, 2, 3, 4, 5]


def test_ordinary_paragraphs_and_divs_do_not_receive_ids():
    result = DOMCleaner().clean_with_mapping("<div><p>Ordinary content</p></div>")

    assert result.element_map == {}
    assert "data-cdom-id" not in result.cleaned_html


def test_elements_with_role_receive_ids():
    result = DOMCleaner().clean_with_mapping('<div role="button">Open</div>')

    assert 'data-cdom-id="1"' in result.cleaned_html
    assert result.element_map[1].role == "button"


def test_html_id_is_preserved_separately_from_synthetic_id():
    result = DOMCleaner().clean_with_mapping('<button id="buy-now">Buy now</button>')

    assert 'id="buy-now"' in result.cleaned_html
    assert 'data-cdom-id="1"' in result.cleaned_html
    assert result.element_map[1].html_id == "buy-now"


def test_generated_ids_are_deterministic():
    html = '<a href="/one">One</a><button>Two</button>'

    first = DOMCleaner().clean_with_mapping(html)
    second = DOMCleaner().clean_with_mapping(html)

    assert first.cleaned_html == second.cleaned_html
    assert first.element_map == second.element_map


def test_removed_elements_are_not_in_the_mapping():
    html = '<nav><a href="/discard">Discard</a></nav><a href="/keep">Keep</a>'

    result = DOMCleaner().clean_with_mapping(html)

    assert "Discard" not in result.cleaned_html
    assert len(result.element_map) == 1
    assert result.element_map[1].href == "/keep"


def test_unwrapped_content_is_mapped_from_the_final_dom():
    cleaner = DOMCleaner(unwrap_tags={"span"})
    result = cleaner.clean_with_mapping('<span><a href="/continue">Continue</a></span>')

    assert "<span" not in result.cleaned_html
    assert "Continue" in result.cleaned_html
    assert len(result.element_map) == 1
    assert result.element_map[1].tag == "a"


def test_synthetic_mapping_attribute_survives_cleaning():
    result = DOMCleaner().clean_with_mapping('<a href="/help">Help</a>')

    assert 'data-cdom-id="1"' in result.cleaned_html
    assert result.element_map[1].cdom_id == 1


def test_arbitrary_data_attributes_are_still_removed():
    html = '<a href="/help" data-track="campaign" data-cdom-id="900">Help</a>'

    result = DOMCleaner().clean_with_mapping(html)

    assert "data-track" not in result.cleaned_html
    assert 'data-cdom-id="900"' not in result.cleaned_html
    assert 'data-cdom-id="1"' in result.cleaned_html


def test_unicode_text_is_normalized_in_element_info():
    result = DOMCleaner().clean_with_mapping("<button>Καλημέρα\n κόσμε 👋</button>")

    assert result.element_map[1].text == "Καλημέρα κόσμε 👋"


def test_long_element_text_is_truncated():
    result = DOMCleaner().clean_with_mapping("<button>" + ("word " * 100) + "</button>")
    text = result.element_map[1].text

    assert len(text) <= 240
    assert text.endswith("…")


def test_malformed_html_is_cleaned_before_mapping():
    result = DOMCleaner().clean_with_mapping('<div><a href="/next">Next<button>Go')

    assert "Next" in result.cleaned_html
    assert "Go" in result.cleaned_html
    assert [info.cdom_id for info in result.element_map.values()] == [1, 2]


def test_empty_html_returns_empty_mapping():
    result = DOMCleaner().clean_with_mapping("")

    assert result.cleaned_html == ""
    assert result.element_map == {}


def test_preserved_iframe_receives_an_id():
    result = DOMCleaner(remove_tags=set()).clean_with_mapping(
        '<iframe title="Example"></iframe>'
    )

    assert result.element_map[1].tag == "iframe"
    assert 'data-cdom-id="1"' in result.cleaned_html


def test_mapping_and_result_are_immutable():
    result = DOMCleaner().clean_with_mapping("<button>Go</button>")

    with pytest.raises(TypeError):
        cast(dict[int, ElementInfo], result.element_map)[2] = result.element_map[1]
    with pytest.raises(FrozenInstanceError):
        attribute = "text"
        setattr(result.element_map[1], attribute, "Changed")


def test_result_stats_describe_the_html_with_synthetic_ids():
    result = DOMCleaner().clean_with_mapping('<a href="/home">Home</a>')

    assert result.stats.output_chars == len(result.cleaned_html)
    assert result.stats.input_tokens is None
