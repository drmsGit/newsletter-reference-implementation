"""Tests for the subject/preheader task's pure logic (ADR-141 §3).

Parsing and mock-format imitation are the two fragile pieces here and neither
needs a database, so they are tested directly. The spend gate in ai/service.py
is DB-backed and covered by manual verification for now.
"""

from app.ai.adapters.mock import imitate_requested_format
from app.ai.tasks.subject_preheader import parse_options


class TestParseOptions:

    def test_parses_the_requested_format(self):
        text = (
            "1. SUBJECT: Early mornings at Praia da Marinha\n"
            "   PREHEADER: The cliffs hold shade until nine\n"
            "2. SUBJECT: Beat the Algarve crowds\n"
            "   PREHEADER: Parking fills before the sun does\n"
        )
        options = parse_options(text)

        assert len(options) == 2
        assert options[0]["subject"] == "Early mornings at Praia da Marinha"
        assert options[0]["preheader"] == "The cliffs hold shade until nine"
        assert options[1]["subject"] == "Beat the Algarve crowds"

    def test_tolerates_a_missing_preheader(self):
        # A model that drifts from the layout should cost us an option's
        # preheader, never an exception in the request path.
        options = parse_options("1. SUBJECT: Only a subject here")

        assert len(options) == 1
        assert options[0]["preheader"] == ""

    def test_ignores_surrounding_chatter(self):
        text = (
            "Sure! Here are three options:\n"
            "1. SUBJECT: A real one\n"
            "   PREHEADER: With a preheader\n"
            "Let me know if you want more.\n"
        )
        assert len(parse_options(text)) == 1

    def test_empty_and_unparseable_input_yield_no_options(self):
        assert parse_options("") == []
        assert parse_options("no recognisable structure at all") == []


class TestMockImitatesRequestedFormat:

    def test_reproduces_the_prompts_own_layout(self):
        # The mock reads the format from the prompt rather than knowing about
        # subjects, so the task's real parser gets something in the right shape.
        prompt = (
            "Return exactly 3 options in this format:\n"
            "1. SUBJECT: <subject>\n"
            "   PREHEADER: <preheader>\n"
        )
        produced = imitate_requested_format(prompt)

        assert produced is not None
        options = parse_options(produced)
        assert len(options) == 3
        assert options[0]["subject"] == "Mock subject 1"
        assert options[2]["preheader"] == "Mock preheader 3"

    def test_returns_none_when_no_format_is_demonstrated(self):
        assert imitate_requested_format("Just write me something nice.") is None

    def test_works_for_a_format_it_was_never_told_about(self):
        # The point of reading the prompt: a future task gets this for free.
        prompt = "Answer as:\nTAG: <tag>\nREASON: <reason>\n"
        produced = imitate_requested_format(prompt, options=2)

        assert produced is not None
        assert "Mock tag 1" in produced
        assert "Mock reason 2" in produced
