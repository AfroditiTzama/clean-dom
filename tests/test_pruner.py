import pytest

from clean_dom import DOMCleaner


def test_dom_cleaner_removes_scripts_and_styles():
    html = """
    <html>
      <head>
        <style>body { color: red; }</style>
        <script>console.log('hi');</script>
      </head>
      <body>
        <div id="test" class="container" onclick="alert()">Hello</div>
      </body>
    </html>
    """

    cleaner = DOMCleaner()
    result = cleaner.clean(html)

    assert "<style" not in result
    assert "<script" not in result
    assert "onclick" not in result
    assert 'id="test"' in result
    assert 'class="container"' in result
    assert "Hello" in result


def test_deprecated_strip_tags_still_works():
    html = '<div class="keep"><span>Text</span></div>'

    with pytest.warns(DeprecationWarning):
        cleaner = DOMCleaner(
            strip_tags={"span"},
            allowed_attributes={"class"},
        )

    result = cleaner.clean(html)

    assert "<span" not in result
    assert "Text" not in result
    assert 'class="keep"' in result


def test_legacy_positional_arguments_remain_compatible():
    html = '<script>remove</script><div class="keep" title="drop">Text</div>'

    with pytest.warns(DeprecationWarning):
        cleaner = DOMCleaner({"script"}, {"class"})

    result = cleaner.clean(html)

    assert "<script" not in result
    assert "remove" not in result
    assert 'class="keep"' in result
    assert "title=" not in result


def test_strip_tags_instance_attribute_remains_compatible():
    cleaner = DOMCleaner(remove_tags={"script"})

    with pytest.warns(DeprecationWarning):
        assert cleaner.strip_tags == {"script"}

    with pytest.warns(DeprecationWarning):
        cleaner.strip_tags = {"style"}

    result = cleaner.clean("<script>keep</script><style>remove</style>")

    assert "<script>" in result
    assert "<style>" not in result


def test_remove_tags_replaces_defaults():
    html = """
    <script>console.log("keep me")</script>
    <aside>Remove me</aside>
    """

    cleaner = DOMCleaner(remove_tags={"aside"})
    result = cleaner.clean(html)

    assert "<aside" not in result
    assert "Remove me" not in result

    # Because remove_tags replaces the defaults, script remains.
    assert "<script" in result
    assert "keep me" in result


def test_empty_remove_tags_means_remove_nothing():
    html = """
    <script>console.log("hello")</script>
    <p>Text</p>
    """

    cleaner = DOMCleaner(remove_tags=set())
    result = cleaner.clean(html)

    assert "<script" in result
    assert "hello" in result
    assert "Text" in result


def test_additional_remove_tags_keep_defaults():
    html = """
    <html>
      <body>
        <script>alert("test")</script>
        <aside>Advertisement</aside>
        <p>Hello</p>
      </body>
    </html>
    """

    cleaner = DOMCleaner(
        additional_remove_tags={"aside"}
    )

    result = cleaner.clean(html)

    assert "<script" not in result
    assert "alert" not in result

    assert "<aside" not in result
    assert "Advertisement" not in result

    assert "Hello" in result


def test_unwrap_tag_preserves_content():
    html = """
    <p>Hello <span>beautiful <strong>world</strong></span></p>
    """

    cleaner = DOMCleaner(
        unwrap_tags={"span"}
    )

    result = cleaner.clean(html)

    assert "<span" not in result
    assert "beautiful" in result
    assert "<strong>world</strong>" in result


def test_allowed_attributes_are_preserved():
    html = """
    <input
        id="email"
        type="email"
        name="email"
        placeholder="Enter your email"
        required
        data-tracking="123"
        onclick="track()"
    >
    """

    cleaner = DOMCleaner()
    result = cleaner.clean(html)

    assert 'id="email"' in result
    assert 'type="email"' in result
    assert 'name="email"' in result
    assert 'placeholder="Enter your email"' in result
    assert "required" in result

    assert "data-tracking" not in result
    assert "onclick" not in result


def test_semantic_form_and_aria_attributes_are_preserved():
    html = """
    <form id="login" action="/login" method="post">
        <label for="email">Email</label>
        <input id="email" name="email" type="email" required checked disabled>
        <select name="plan"><option selected>Basic</option></select>
        <button aria-label="Submit" aria-labelledby="submit-label" role="button">
            Submit
        </button>
    </form>
    """

    result = DOMCleaner().clean(html)

    for attribute in (
        'id="login"',
        'action="/login"',
        'method="post"',
        'for="email"',
        'name="email"',
        'type="email"',
        "required",
        "checked",
        "disabled",
        'name="plan"',
        "selected",
        'aria-label="Submit"',
        'aria-labelledby="submit-label"',
        'role="button"',
    ):
        assert attribute in result


def test_custom_allowed_attributes():
    html = """
    <div
        id="remove-id"
        class="keep"
        title="remove-title"
        data-custom="remove"
    >
        Hello
    </div>
    """

    cleaner = DOMCleaner(
        allowed_attributes={"class"}
    )

    result = cleaner.clean(html)

    assert 'class="keep"' in result
    assert "id=" not in result
    assert "title=" not in result
    assert "data-custom" not in result


def test_comments_are_removed_by_default():
    html = """
    <div>
        Hello
        <!-- tracking information -->
        World
    </div>
    """

    cleaner = DOMCleaner()
    result = cleaner.clean(html)

    assert "tracking information" not in result
    assert "Hello" in result
    assert "World" in result


def test_comments_can_be_preserved():
    html = """
    <div>
        Hello
        <!-- keep this comment -->
    </div>
    """

    cleaner = DOMCleaner(
        remove_comments=False
    )

    result = cleaner.clean(html)

    assert "keep this comment" in result


def test_data_urls_are_removed_by_default():
    html = """
    <img
        src="data:image/png;base64,VERY_LONG_IMAGE_DATA"
        alt="Example image"
    >
    <a href="data:text/html,unsafe">Example link</a>
    """

    cleaner = DOMCleaner()
    result = cleaner.clean(html)

    assert "data:image" not in result
    assert "data:text" not in result
    assert 'alt="Example image"' in result


def test_data_urls_can_be_preserved():
    html = """
    <img
        src="data:image/png;base64,ABC123"
        alt="Image"
    >
    <a href="data:text/plain,ABC123">Text</a>
    """

    cleaner = DOMCleaner(
        drop_data_urls=False
    )

    result = cleaner.clean(html)

    assert "data:image/png;base64,ABC123" in result
    assert "data:text/plain,ABC123" in result


def test_long_attributes_are_removed():
    html = """
    <a href="https://example.com/this/is/a/very/long/url">
        Link
    </a>
    """

    cleaner = DOMCleaner(
        max_attribute_length=10
    )

    result = cleaner.clean(html)

    assert "href=" not in result
    assert "Link" in result


def test_attribute_length_limit_can_be_disabled():
    long_url = "https://example.com/" + ("a" * 1000)

    html = f'<a href="{long_url}">Link</a>'

    cleaner = DOMCleaner(
        max_attribute_length=None
    )

    result = cleaner.clean(html)

    assert long_url in result
    assert "Link" in result


def test_remove_tags_and_strip_tags_cannot_be_used_together():
    with pytest.raises(ValueError):
        DOMCleaner(
            remove_tags={"script"},
            strip_tags={"style"},
        )


def test_malformed_html():
    html = """
    <div>
        <p>
            Unclosed paragraph
            <span>nested
        </p>
    </div>
    """

    cleaner = DOMCleaner()
    result = cleaner.clean(html)

    assert "Unclosed paragraph" in result
    assert "nested" in result


def test_minimal_preset():
    cleaner = DOMCleaner.preset("minimal")

    html = """
    <a
        id="link"
        href="/docs"
        class="button"
        title="Documentation"
    >
        Docs
    </a>
    """

    result = cleaner.clean(html)

    assert 'id="link"' in result
    assert 'href="/docs"' in result

    assert "class=" not in result
    assert "title=" not in result


def test_content_preset():
    cleaner = DOMCleaner.preset("content")

    html = """
    <main>
        <p>Hello <span>world</span></p>
        <aside>Advertisement</aside>
    </main>
    """

    result = cleaner.clean(html)

    assert "<span" not in result
    assert "world" in result

    assert "<aside" not in result
    assert "Advertisement" not in result


def test_agent_preset_preserves_agent_attributes():
    cleaner = DOMCleaner.preset("agent")

    html = """
    <button
        id="submit"
        type="submit"
        role="button"
        aria-label="Submit form"
        data-tracking="123"
    >
        Submit
    </button>
    """

    result = cleaner.clean(html)

    assert 'id="submit"' in result
    assert 'type="submit"' in result
    assert 'role="button"' in result
    assert 'aria-label="Submit form"' in result

    assert "data-tracking" not in result


def test_unknown_preset_raises_error():
    with pytest.raises(ValueError):
        DOMCleaner.preset("does-not-exist")


@pytest.mark.parametrize(
    "input_html, expected_substring",
    [
        ("", ""),
        ("   ", ""),
        ("<div>Hello World</div>", "Hello World"),
        (
            "<script>var x = 1;</script><span>Clean</span>",
            "<span>Clean</span>",
        ),
        ("<p>Καλημέρα κόσμε</p>", "Καλημέρα κόσμε"),
        ("<p>Hello 👋</p>", "Hello 👋"),
    ],
)
def test_edge_cases(input_html, expected_substring):
    cleaner = DOMCleaner()

    result = cleaner.clean(input_html)

    assert expected_substring in result