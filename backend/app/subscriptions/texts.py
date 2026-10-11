"""Every word a recipient reads around unsubscribing (ADR-191 point 7).

English only for now, and all of it here — the footer line, the page, the
confirmation — so translating it later is an addition to this file rather than
a search through the code. Every value that comes from data is escaped.
"""
from markupsafe import escape

FOOTER_STYLE = "font-size:12px;color:#666666;text-align:center;margin:24px 0 0;"


def footer_html(brand: str, url: str) -> str:
    """The unsubscribe line of frames made before brand profiles (ADR-191
    point 5). Since frame version 3 every email ends with the profile's legal
    footer instead (`storage/modules/email/_legal_footer.html`, ADR-194).

    **Never change this line, or `FOOTER_STYLE`.** Deliveries sent with it
    rebuild to their stored hash only if it renders byte for byte as it did,
    and this file is not in the template fingerprint: a change would break
    `hash_matches` for every one of them while `templates_match` still said the
    layout was unchanged (ADR-183; ADR-194 addenda of 2026-10-11)."""
    return (
        f'<p style="{FOOTER_STYLE}">You receive this from {escape(brand)}. '
        f'<a href="{escape(url)}">Unsubscribe</a>.</p>'
    )


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex">
    <title>{escape(title)}</title>
    <style>
      body {{ font-family: system-ui, sans-serif; max-width: 32rem; margin: 4rem auto; padding: 0 1rem; color: #222; }}
      button {{ font: inherit; padding: .6rem 1rem; margin: .25rem 0; cursor: pointer; }}
      .quiet {{ color: #666; }}
    </style>
  </head>
  <body>
    {body}
  </body>
</html>"""


def confirm_page(brand: str, action_url: str, *, offer_everything: bool) -> str:
    """Opening the link shows this; only a button opts out (ADR-191 point 3),
    so a link scanner opening every link unsubscribes nobody."""
    everything = (
        '<p><button type="submit" name="scope" value="everything">'
        "Unsubscribe from everything we send</button></p>"
        if offer_everything else ""
    )
    return _page(
        f"Unsubscribe from {brand}",
        f"""<h1>Unsubscribe from {escape(brand)} emails?</h1>
    <form method="post" action="{escape(action_url)}">
      <p><button type="submit" name="scope" value="brand">Unsubscribe from {escape(brand)} emails</button></p>
      {everything}
    </form>
    <p class="quiet">Messages you need, such as sign-in codes, are not affected.</p>""",
    )


def done_page(brand: str, *, everything: bool) -> str:
    what = "everything we send" if everything else f"{escape(brand)} emails"
    return _page(
        "You are unsubscribed",
        f"""<h1>You are unsubscribed</h1>
    <p>You will no longer receive {what}.</p>
    <p class="quiet">Messages you need, such as sign-in codes, are not affected.</p>""",
    )


def invalid_page() -> str:
    """The same page for an unknown token and a malformed one: nothing about
    whether a message or a person exists."""
    return _page(
        "Link not valid",
        """<h1>This link is not valid</h1>
    <p class="quiet">It may have been copied incompletely. Use the unsubscribe link in the email itself.</p>""",
    )
