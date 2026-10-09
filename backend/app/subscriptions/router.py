"""The public unsubscribe page (ADR-191), outside the signed-in planes.

**The token in the path is the only credential.** These routes read no session
cookie and act as no principal, so neither the session guard nor CSRF applies:
CSRF protects requests a cookie authorises, and here none does. The policy
table classes the path as RECIPIENT_TOKEN so the boundary stays legible.

**Opening the link changes nothing; only a POST opts out** (point 3), because
link scanners and previews open every link in a mail. A mail client's one-click
button (RFC 8058: a POST with `List-Unsubscribe=One-Click`) opts out at once,
at the default scope — there is no page on which to choose another.
"""
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.settings.service import get_unsubscribe_offer_everything
from app.subscriptions import service, texts

router = APIRouter(include_in_schema=False)


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
def unsubscribe_page(token: str, db: Session = Depends(get_db)):
    found = service.message_for(db, token)
    if found is None:
        return HTMLResponse(texts.invalid_page(), status_code=404)
    _, brand = found
    return HTMLResponse(texts.confirm_page(
        brand.name, service.unsubscribe_path(token),
        offer_everything=get_unsubscribe_offer_everything(db),
    ))


@router.post("/unsubscribe/{token}", response_class=HTMLResponse)
def unsubscribe_confirm(
    token: str,
    db: Session = Depends(get_db),
    scope: str | None = Form(None),
    one_click: str | None = Form(None, alias="List-Unsubscribe"),
):
    # One-click (RFC 8058) carries List-Unsubscribe=One-Click and no scope:
    # the default. The page's buttons carry scope=brand or scope=everything.
    everything = scope == "everything" and one_click is None
    done = service.unsubscribe(db, token, everything=everything)
    if done is None:
        return HTMLResponse(texts.invalid_page(), status_code=404)
    brand, everything_done = done
    return HTMLResponse(texts.done_page(brand.name, everything=everything_done))
