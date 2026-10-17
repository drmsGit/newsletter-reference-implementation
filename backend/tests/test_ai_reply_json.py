"""Reading a JSON answer out of a model's reply (2026-10-17).

The three tasks that ask for JSON (a variant from a topic, a content draft, a
translation) took the text from the first brace to the last. A reply that
holds two objects, as the real model gave when it started over, is then not
JSON at all, and the whole answer was lost.
"""
from app.ai.tasks.base import json_object


def test_one_object_with_prose_around_it():
    assert json_object('Here it is:\n{"a": 1}\nThat is all.') == {"a": 1}


def test_two_objects_give_the_last_whole_one():
    assert json_object('{"a": 1} {"a": 2, "b": [1, 2]}') == {"a": 2, "b": [1, 2]}


def test_braces_inside_strings_and_a_stray_brace_in_prose():
    assert json_object('A { stray brace, then {"text": "a } in it", "n": {"x": 1}}') == {
        "text": "a } in it", "n": {"x": 1}}


def test_a_cut_off_last_object_leaves_the_whole_one_before_it():
    assert json_object('{"a": 1} {"a": 2, "b"') == {"a": 1}


def test_nothing_readable_is_none():
    assert json_object("") is None
    assert json_object("no braces here") is None
    assert json_object("[1, 2, 3]") is None
