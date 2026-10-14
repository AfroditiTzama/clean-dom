from typing import List

import pytest

from clean_dom import DOMCleaner, _tokenizers


class CharacterTokenizer:
    """Deterministic test encoder that treats each character as one token."""

    def encode(self, text: str) -> List[str]:
        return list(text)


@pytest.fixture
def use_character_tiktoken(monkeypatch):
    """Use deterministic token counts without requiring the optional package."""
    monkeypatch.setattr(
        _tokenizers,
        "_get_tiktoken_encoder",
        lambda: CharacterTokenizer(),
    )


def test_budget_already_satisfied_at_level_zero(use_character_tiktoken):
    cleaner = DOMCleaner()
    html = "<p>small page</p>"
    expected = cleaner.clean(html)

    result = cleaner.clean_to_budget(
        html,
        max_tokens=len(expected),
    )

    assert result.cleaned_html == expected
    assert result.stats.output_tokens == len(expected)
    assert result.stats.max_tokens == len(expected)
    assert result.stats.budget_met is True
    assert result.stats.strategy_level == 0


def test_budget_uses_level_two_to_remove_boilerplate(use_character_tiktoken):
    html = (
        "<main><p>Keep this text.</p><aside>"
        + ("Low priority advertisement. " * 20)
        + "</aside></main>"
    )
    expected = DOMCleaner(additional_remove_tags={"aside"}).clean(html)

    result = DOMCleaner().clean_to_budget(html, max_tokens=len(expected))

    assert result.cleaned_html == expected
    assert "Low priority advertisement" not in result.cleaned_html
    assert result.stats.strategy_level == 2
    assert result.stats.budget_met is True


@pytest.mark.parametrize("tag", ["span", "font"])
def test_budget_uses_level_three_to_unwrap_safe_wrappers(
    tag,
    use_character_tiktoken,
):
    html = f"<p><{tag}>Preserve this text.</{tag}></p>"
    expected = "<html><body><p>Preserve this text.</p></body></html>"

    result = DOMCleaner().clean_to_budget(html, max_tokens=len(expected))

    assert result.cleaned_html == expected
    assert result.stats.strategy_level == 3
    assert result.stats.budget_met is True


def test_budget_uses_level_four_to_collapse_redundant_wrappers(
    use_character_tiktoken,
):
    html = "<div>" * 8 + "<p>Visible text remains.</p>" + "</div>" * 8
    expected = DOMCleaner._collapse_redundant_dom(DOMCleaner().clean(html))

    result = DOMCleaner().clean_to_budget(html, max_tokens=len(expected))

    assert result.cleaned_html == expected
    assert result.cleaned_html.count("<div") == 0
    assert "Visible text remains." in result.cleaned_html
    assert result.stats.strategy_level == 4
    assert result.stats.budget_met is True


def test_budget_preserves_semantic_span_attributes(use_character_tiktoken):
    html = '<p><span role="button" aria-label="Submit">Submit</span></p>'

    result = DOMCleaner().clean_to_budget(html, max_tokens=1)

    assert "<span" in result.cleaned_html
    assert 'role="button"' in result.cleaned_html
    assert 'aria-label="Submit"' in result.cleaned_html
    assert "Submit" in result.cleaned_html
    assert result.stats.budget_met is False


def test_impossible_budget_returns_complete_smallest_result(
    use_character_tiktoken,
):
    html = "<p>" + ("Visible text must remain. " * 20) + "</p>"
    expected = DOMCleaner().clean(html)

    result = DOMCleaner().clean_to_budget(html, max_tokens=1)

    assert result.cleaned_html == expected
    assert result.stats.output_tokens is not None
    assert result.stats.output_tokens > 1
    assert result.stats.budget_met is False
    assert result.stats.strategy_level == 0
    assert "Visible text must remain." in result.cleaned_html


@pytest.mark.parametrize("max_tokens", [0, -1, -100])
def test_non_positive_budget_raises_value_error(max_tokens):
    with pytest.raises(ValueError, match="positive integer"):
        DOMCleaner().clean_to_budget("<p>Text</p>", max_tokens=max_tokens)


def test_empty_html_fits_budget_at_level_zero(use_character_tiktoken):
    result = DOMCleaner().clean_to_budget("", max_tokens=1)

    assert result.cleaned_html == ""
    assert result.stats.input_tokens == 0
    assert result.stats.output_tokens == 0
    assert result.stats.budget_met is True
    assert result.stats.strategy_level == 0


def test_unicode_content_is_not_truncated_when_budget_is_impossible(
    use_character_tiktoken,
):
    html = "<p>Καλημέρα κόσμε 👋 你好</p>"

    result = DOMCleaner().clean_to_budget(html, max_tokens=1)

    assert "Καλημέρα κόσμε 👋 你好" in result.cleaned_html
    assert result.stats.budget_met is False
    assert result.stats.output_tokens == len(result.cleaned_html)


def test_malformed_html_is_cleaned_without_cutting_markup(use_character_tiktoken):
    html = "<div><p>Unclosed <span>nested"

    result = DOMCleaner().clean_to_budget(html, max_tokens=1)

    assert "Unclosed" in result.cleaned_html
    assert "nested" in result.cleaned_html
    assert result.cleaned_html.endswith("</body></html>")
    assert result.stats.budget_met is False


def test_budget_mode_preserves_existing_clean_apis_and_configuration(
    use_character_tiktoken,
):
    cleaner = DOMCleaner(
        remove_tags={"script"},
        additional_remove_tags={"custom"},
        remove_comments=False,
        drop_data_urls=False,
        max_attribute_length=None,
    )
    html = "<script>remove</script><div>content</div>"
    remove_tags_before = set(cleaner.remove_tags)
    allowed_attributes_before = set(cleaner.allowed_attributes)
    unwrap_tags_before = set(cleaner.unwrap_tags)

    clean_result = cleaner.clean(html)
    report_result = cleaner.clean_with_report(html)
    budget_result = cleaner.clean_to_budget(html, max_tokens=1)

    assert isinstance(clean_result, str)
    assert report_result.cleaned_html == clean_result
    assert "content" in budget_result.cleaned_html
    assert cleaner.remove_tags == remove_tags_before
    assert cleaner.allowed_attributes == allowed_attributes_before
    assert cleaner.unwrap_tags == unwrap_tags_before
    assert cleaner.remove_comments is False
    assert cleaner.drop_data_urls is False
    assert cleaner.max_attribute_length is None


def test_budget_mode_requires_tiktoken_when_optional_dependency_is_missing(
    monkeypatch,
):
    original_import = __import__

    def import_without_tiktoken(name, *args, **kwargs):
        if name == "tiktoken":
            raise ModuleNotFoundError("No module named 'tiktoken'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", import_without_tiktoken)
    _tokenizers._get_tiktoken_encoder.cache_clear()

    with pytest.raises(ImportError, match=r'pip install "clean-dom\[tokens\]"'):
        DOMCleaner().clean_to_budget("<p>Text</p>", max_tokens=10)

    _tokenizers._get_tiktoken_encoder.cache_clear()


def test_budget_mode_uses_tiktoken_when_optional_dependency_is_installed():
    tiktoken = pytest.importorskip("tiktoken")
    html = "<script>remove</script><p>Keep this text.</p>"
    cleaned_html = DOMCleaner().clean(html)
    expected_tokens = len(tiktoken.get_encoding("cl100k_base").encode(cleaned_html))

    result = DOMCleaner().clean_to_budget(html, max_tokens=expected_tokens)

    assert result.cleaned_html == cleaned_html
    assert result.stats.output_tokens == expected_tokens
    assert result.stats.budget_met is True
    assert result.stats.strategy_level == 0
