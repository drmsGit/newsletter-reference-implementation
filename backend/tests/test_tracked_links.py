"""A link names the content it belongs to (task-240; ADR-182, ADR-102)."""
import pytest

from app.delivery.providers.factory import providers_for_channel
from app.providers.adapters.resend import parse_webhook
from app.rendering.service import module_html
from app.rendering.tracking import CONTENT_PARAM, content_id_from_url, tag_links, with_content_id


class TestTheCarrier:
    def test_a_link_gains_the_parameter_and_keeps_its_query_and_fragment(self):
        url = with_content_id("https://example.com/a?utm=x#top", 42)
        assert url == "https://example.com/a?utm=x&nl_content=42#top"
        assert content_id_from_url(url) == 42

    def test_an_existing_parameter_is_replaced_not_duplicated(self):
        url = with_content_id("https://example.com/a?nl_content=1", 42)
        assert url.count(CONTENT_PARAM) == 1 and content_id_from_url(url) == 42

    @pytest.mark.parametrize("url", [None, "", "https://example.com/", "https://e.com/?nl_content=abc"])
    def test_no_id_reads_as_none(self, url):
        assert content_id_from_url(url) is None

    def test_only_http_links_are_tagged(self):
        html = '<a href="https://e.com/x">x</a><a href="mailto:a@b.c">m</a><a href="#top">t</a>'
        tagged = tag_links(html, 7)
        assert 'href="https://e.com/x?nl_content=7"' in tagged
        assert 'href="mailto:a@b.c"' in tagged and 'href="#top"' in tagged


class TestRendering:
    def test_a_content_module_links_name_their_content(self):
        html = module_html("email", "img_left", 1, {
            "headline_medium": "H", "button_label": "Go", "button_url": "https://e.com/read"},
            content_id=55)
        assert "https://e.com/read?nl_content=55" in html

    def test_a_static_module_link_names_nothing(self):
        html = module_html("email", "cta", 2, {"label": "Go", "url": "https://e.com/static"})
        assert "https://e.com/static" in html and CONTENT_PARAM not in html


class TestTheResendAdapter:
    def _click(self, link):
        return parse_webhook({"type": "email.clicked", "created_at": "t",
                              "data": {"email_id": "m-1", "click": {"link": link}}})

    def test_a_tracked_click_names_its_content(self):
        assert self._click("https://e.com/read?nl_content=55").event_data["content_record_id"] == 55

    def test_an_untracked_click_names_nothing(self):
        assert "content_record_id" not in self._click("https://e.com/logo").event_data


def test_the_capability_is_declared_per_provider():
    declared = {p["name"]: p["click_content_attribution"] for p in providers_for_channel("email")}
    assert declared == {"mock": False, "resend": True}
