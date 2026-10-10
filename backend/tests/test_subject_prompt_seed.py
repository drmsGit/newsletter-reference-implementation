"""The shipped subject-line prompt is a neutral seed (task-339).

The one worked example of "the manager owns the prompt" (ADR-140/141) shipped a
developer's English house style — "no exclamation marks, no 'Discover', no
emoji", "be concrete". Decided 2026-10-09 (business baseline P2-H1): the seed
keeps only what the code needs (the three-option format the reply is parsed in)
and the technical limits; a marked line awaits the company's own house style;
and the model writes in the language of the content.
"""
from app.ai.tasks.subject_preheader import DEFAULT_PROMPT, REQUESTED_OPTIONS, parse_options


def test_no_editorial_taste_ships_with_it():
    lowered = DEFAULT_PROMPT.lower()
    for taste in ("exclamation", "discover", "emoji", "be concrete", "never repeat"):
        assert taste not in lowered, taste


def test_it_keeps_the_limits_and_the_parsed_format():
    assert "60 characters" in DEFAULT_PROMPT and "90 characters" in DEFAULT_PROMPT
    for n in range(1, REQUESTED_OPTIONS + 1):
        assert f"{n}. SUBJECT: <subject>" in DEFAULT_PROMPT
    assert DEFAULT_PROMPT.count("PREHEADER: <preheader>") == REQUESTED_OPTIONS
    assert "{content}" in DEFAULT_PROMPT


def test_it_leaves_a_marked_place_for_the_companys_house_style():
    assert "Your house style:" in DEFAULT_PROMPT


def test_it_asks_for_the_language_of_the_content():
    assert "language the content is written in" in DEFAULT_PROMPT


def test_a_reply_in_the_seeds_format_still_parses():
    reply = "\n".join(f"{n}. SUBJECT: Betreff {n}\n   PREHEADER: Vorschau {n}" for n in range(1, 4))
    assert [o["subject"] for o in parse_options(reply)] == ["Betreff 1", "Betreff 2", "Betreff 3"]
