"""Profile link extras must not attribute non-content clicks (ADR-182, ADR-194)."""
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import pytest

from app.brand_profiles.theme import link_params
from app.rendering.service import email_document, module_html
from app.rendering.tracking import content_id_from_url
from tests.test_header_footer import HEADER_FOOTER


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.urls.extend(value for key, value in attrs if key == "href")


@pytest.mark.parametrize("module_type,variables", [
    ("cta", {"label": "Shop", "url": "https://example.test/shop"}),
    ("header", {}),
    ("footer", {"footer_note": "This email's note"}),
])
def test_profile_extras_cannot_attribute_a_non_content_module(module_type, variables):
    # These values can already exist in a profile: optional extras were saved
    # as arbitrary key=value pairs. Rendering must keep attribution separate
    # even for stored values, without relying on a later profile save.
    values = {**HEADER_FOOTER, "utm_extra": "nl_content=424242\nref=newsletter"}
    theme = {"values": values, "link_params": link_params(values, "Spring", "A")}
    body = email_document([module_html("email", module_type, 77, variables, theme=theme)], theme=theme)
    links = Links()
    links.feed(body)
    assert links.urls, "the regression must exercise an actual rendered link"
    for url in links.urls:
        params = parse_qs(urlsplit(url).query)
        assert params.get("utm_source") == ["newsletter"]
        assert params.get("ref") == ["newsletter"]
        assert "nl_content" not in params, "profile extras gave a non-content link attribution"
        assert content_id_from_url(url) is None
