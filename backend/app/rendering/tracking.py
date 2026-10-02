"""A link names the content it belongs to (task-240; ADR-182 points 4-5, ADR-102).

ADR-182 made a click credit content only when the link names it, which paused
click learning: no rendered link named anything. This is the carrier ADR-102
decided rendering should prepare — a query parameter, chosen 2026-10-02 because
it survives every provider that reports the clicked URL (Resend does), and it
names only an internal content id, never the recipient.

Only links inside a content-bound module are tagged. A logo, a footer, a
static call-to-action belong to no content and stay untagged, so a click on
them credits nothing — ADR-182 point 3.
"""
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

#: The parameter a tracked link carries. Part of the contract with every
#: provider adapter that reads clicked URLs back.
CONTENT_PARAM = "nl_content"

_HREF = re.compile(r'href="(https?://[^"]+)"', re.IGNORECASE)


def with_content_id(url: str, content_id: int) -> str:
    """`url` with `nl_content=<content_id>` — replacing one already there, and
    keeping the rest of the query and the fragment as they were."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != CONTENT_PARAM]
    query.append((CONTENT_PARAM, str(content_id)))
    return urlunsplit(parts._replace(query=urlencode(query)))


def tag_links(html: str, content_id: int) -> str:
    """Every http(s) link in `html` tagged with `content_id`. `mailto:`,
    anchors and relative links are left alone: none of them is a click a
    provider reports as content engagement."""
    return _HREF.sub(lambda m: f'href="{with_content_id(m.group(1), content_id)}"', html)


def content_id_from_url(url: str | None) -> int | None:
    """The content id a clicked URL names, or None — absent, empty, or not an
    integer all answer None rather than raising: a malformed link is a click
    that credits nothing, not an error."""
    if not url:
        return None
    for key, value in parse_qsl(urlsplit(url).query):
        if key == CONTENT_PARAM:
            try:
                return int(value)
            except ValueError:
                return None
    return None
