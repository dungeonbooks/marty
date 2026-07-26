"""Tests for auto-embedding books Marty names in prose."""

import pytest

from src.discord_bot.bot import (
    _BOLD_TITLE,
    _is_embeddable,
    _normalize_title,
    _titles_match,
)


class TestTitleExtraction:
    def test_pulls_bolded_titles_in_order(self):
        text = (
            "looks like Khaw's newest is **Find Me Where It Ends** - 2026. "
            "before that she had **The Library at Hellebore** (2025)."
        )

        assert _BOLD_TITLE.findall(text) == [
            "Find Me Where It Ends",
            "The Library at Hellebore",
        ]

    def test_ignores_unbolded_mentions(self):
        assert _BOLD_TITLE.findall("Between Two Fires by Buehlman is great") == []

    def test_ignores_bold_spanning_lines(self):
        assert _BOLD_TITLE.findall("**not\na title**") == []

    def test_ignores_trivially_short_bold(self):
        assert _BOLD_TITLE.findall("**hi** there") == []


class TestTitleMatching:
    @pytest.mark.parametrize(
        "mentioned,resolved",
        [
            ("Between Two Fires", "Between Two Fires"),
            ("The Blacktongue Thief", "The Blacktongue Thief: A Novel"),
            ("dune", "Dune"),
            ("The Library at Hellebore", "Library at Hellebore"),
        ],
    )
    def test_accepts_real_matches(self, mentioned, resolved):
        assert _titles_match(mentioned, resolved)

    @pytest.mark.parametrize(
        "mentioned,resolved",
        [
            # Bold used for emphasis, not a title - this is the case that would
            # otherwise make Marty cite a book he never named.
            ("yeah, basically", "Falling in Love with Where You Are"),
            ("Between Two Fires", "The Lesser Dead"),
            ("", "Dune"),
        ],
    )
    def test_rejects_wrong_matches(self, mentioned, resolved):
        assert not _titles_match(mentioned, resolved)


class TestEmbeddability:
    def test_stub_record_rejected(self):
        assert not _is_embeddable({"title": "Black Tongue Thief"})

    def test_record_with_any_real_metadata_accepted(self):
        assert _is_embeddable({"title": "Dune", "author": "Frank Herbert"})
        assert _is_embeddable({"title": "Dune", "rating": 4.2})

    def test_untitled_rejected(self):
        assert not _is_embeddable({"author": "Frank Herbert"})


class TestNormalization:
    def test_strips_punctuation_and_case(self):
        assert _normalize_title("The Blacktongue Thief!") == "the blacktongue thief"

    def test_dedup_key_is_stable_across_punctuation(self):
        assert _normalize_title("Dune: A Novel") == _normalize_title("dune a novel")
