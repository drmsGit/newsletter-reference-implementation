"""Rich-text formatting must preserve a link's destination (task-392 item 6)."""
from html.parser import HTMLParser

import pytest

from app.rendering.service import render_rich_text


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.targets.append(dict(attrs).get("href"))


@pytest.mark.parametrize("prefix", ["", "- "], ids=["inline", "bullet"])
def test_italic_syntax_inside_a_link_target_is_literal(prefix):
    # Asterisks are valid URL characters, for example in a search expression.
    # Formatting the already-built anchor inserts <em> into its href instead.
    target = "https://example.test/search?q=*walking*&page=2"
    rendered = str(render_rich_text(f"{prefix}[Search]({target})"))
    links = Links()
    links.feed(rendered)
    assert links.targets == [target]
