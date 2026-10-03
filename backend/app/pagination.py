"""One way to page a list (ADR-185, task-88).

A list whose length grows with use of the system is paged; one fixed by code
or configuration stays a plain array (point 1). A paged route returns one
envelope, `{items, total, limit, offset}`, with the total in the body so it is
part of the typed contract the React client is generated from (point 2,
ADR-170 point 4). This module is the single mechanism point 3 asks for: no
route defines its own paging parameters or its own paged shape.
"""
from dataclasses import dataclass
from typing import Callable, Generic, Iterable, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@dataclass(frozen=True)
class PageParams:
    limit: int
    offset: int


def page_params(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Rows per page (1-200)."),
    offset: int = Query(0, ge=0, description="Rows to skip."),
) -> PageParams:
    """The paging query parameters, declared once (ADR-185 point 3).
    A route takes `params: PageParams = Depends(page_params)`."""
    return PageParams(limit=limit, offset=offset)


class Page(BaseModel, Generic[T]):
    """One page of a list that grows with use (ADR-185 point 2).

    `total` is the size of the whole filtered set, counted with the same
    filters as `items` (point 6), so "page 3 of 7" and the last page are known.
    """

    items: list[T]
    total: int
    limit: int
    offset: int


def page_of_query(query, params: PageParams, *order, convert: Callable = lambda row: row) -> Page:
    """Page a SQLAlchemy query in the database.

    `order` is the route's declared order; it MUST end with the model's `id`
    as the tie-breaker (ADR-185 point 4), so pages neither overlap nor skip.
    The total is the same query, unordered and unsliced — the same filters,
    by construction.
    """
    total = query.order_by(None).count()
    rows = query.order_by(*order).offset(params.offset).limit(params.limit).all()
    return Page(items=[convert(r) for r in rows], total=total,
                limit=params.limit, offset=params.offset)


def page_of_list(rows: Iterable, params: PageParams) -> Page:
    """Page a list a route has already assembled in Python.

    For read models built from several queries (campaign monitoring, groups
    with counts). The total is honest; the work is not saved — every row was
    computed to be counted. Acceptable at ADR-185 point 5's scale, and the
    reason a route that CAN page in SQL should use `page_of_query`.
    """
    rows = list(rows)
    window = rows[params.offset:params.offset + params.limit]
    return Page(items=window, total=len(rows), limit=params.limit, offset=params.offset)
