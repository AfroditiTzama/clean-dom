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
    
    assert "<style>" not in result
    assert "<script>" not in result
    assert 'onclick' not in result
    assert 'id="test"' in result
    assert 'class="container"' in result
    assert "Hello" in result

def test_custom_strip_and_attributes():
    html = '<div class="keep" data-custom="remove"><span>Text</span></div>'
    cleaner = DOMCleaner(
        strip_tags={"span"},
        allowed_attributes={"class"}
    )
    result = cleaner.clean(html)
    
    assert "<span>" not in result
    assert "Text" not in result
    assert 'class="keep"' in result
    assert 'data-custom' not in result

def test_malformed_html():
    html = "<div><p>Unclosed paragraph <span>nested</p></div>"
    cleaner = DOMCleaner()
    result = cleaner.clean(html)
    
    assert "Unclosed paragraph" in result

@pytest.mark.parametrize("input_html, expected_substring", [
    ("", ""),
    ("<div>Hello World</div>", "Hello World"),
    ("<script>var x = 1;</script><span>Clean</span>", "<span>Clean</span>"),
])
def test_edge_cases(input_html, expected_substring):
    cleaner = DOMCleaner()
    result = cleaner.clean(input_html)
    assert expected_substring in result