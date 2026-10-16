from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExpressionCase(BaseModel):
    """One case: when `field` `is` filled, empty, or equals `value`, `text`."""

    model_config = ConfigDict(populate_by_name=True)

    field: str = Field(description="gender, first_name or last_name")
    is_: str = Field(alias="is", description="filled, empty or equals")
    value: str | None = Field(None, description="For equals only; gender is female, male or diverse")
    text: str = Field(description="May print {{first_name}} and {{last_name}}")


class ExpressionLanguage(BaseModel):
    cases: list[ExpressionCase] = []
    fallback: str = Field(description="For recipients no case fits; prints no recipient field")


class ExpressionEntry(BaseModel):
    id: int
    name: str = Field(description="What a text writes between {{ and }}; fixed once created")
    label: str
    languages: dict[str, ExpressionLanguage]
    updated_at: datetime = Field(description="The version token for If-Match")


class ExpressionDictionary(BaseModel):
    items: list[ExpressionEntry]
    may_manage: bool = Field(description="Whether this person may change the dictionary")


class ExpressionEntryCreate(BaseModel):
    name: str
    label: str
    languages: dict[str, ExpressionLanguage]


class ExpressionEntryUpdate(BaseModel):
    label: str
    languages: dict[str, ExpressionLanguage]


def stored(languages: dict[str, ExpressionLanguage]) -> dict:
    """The languages as the table and the rules hold them."""
    return {code: spec.model_dump(by_alias=True, exclude_none=True) for code, spec in languages.items()}
