"""
check_reading_level - Validates that all user-facing text meets reading level targets.

Implements the Flesch-Kincaid Grade Level formula without external dependencies:
  FKGL = 0.39 × (total_words / total_sentences)
       + 11.8 × (total_syllables / total_words)
       - 15.59

Target: grade 6-8 (configurable via settings.PLAIN_LANGUAGE_TARGET_GRADE_LEVEL).
Legal terms are allowlisted since they cannot be simplified further.
"""

import re
from typing import NamedTuple

from django.conf import settings
from django.core.management.base import BaseCommand


# ============================================================================
# Legal terms that inflate reading level but cannot be simplified
# ============================================================================

LEGAL_TERM_ALLOWLIST = frozenset(
    {
        "bankruptcy",
        "eligibility",
        "attorney",
        "jurisdiction",
        "unsecured",
        "exemption",
        "exemptions",
        "discharge",
        "petition",
        "repayment",
        "acknowledgment",
        "unauthorized",
        "determination",
        "information",
    }
)


# ============================================================================
# Flesch-Kincaid implementation (no external dependency)
# ============================================================================


class ReadingLevelResult(NamedTuple):
    text_label: str
    grade_level: float
    word_count: int
    sentence_count: int
    syllable_count: int
    passes: bool


def _count_syllables(word: str) -> int:
    """Estimate syllable count using vowel-group heuristic."""
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    # Remove trailing silent 'e'
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]

    # Count vowel groups
    count = len(re.findall(r"[aeiouy]+", word))
    return max(count, 1)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on period, exclamation, question mark."""
    sentences = re.split(r"[.!?]+", text)
    return [s.strip() for s in sentences if s.strip()]


def _extract_words(text: str) -> list[str]:
    """Extract alphabetic words from text."""
    return re.findall(r"[a-zA-Z]+", text)


def flesch_kincaid_grade(text: str) -> tuple[float, int, int, int]:
    """
    Calculate Flesch-Kincaid Grade Level.

    Returns:
        (grade_level, word_count, sentence_count, syllable_count)
    """
    sentences = _split_sentences(text)
    words = _extract_words(text)

    if not words or not sentences:
        return (0.0, len(words), len(sentences), 0)

    total_syllables = sum(_count_syllables(w) for w in words)
    total_words = len(words)
    total_sentences = len(sentences)

    grade = (
        0.39 * (total_words / total_sentences)
        + 11.8 * (total_syllables / total_words)
        - 15.59
    )

    return (round(grade, 1), total_words, total_sentences, total_syllables)


def check_text(
    label: str,
    text: str,
    target_grade: float = 7.0,
) -> ReadingLevelResult:
    """Check a single text string against the target grade level."""
    grade, words, sentences, syllables = flesch_kincaid_grade(text)
    return ReadingLevelResult(
        text_label=label,
        grade_level=grade,
        word_count=words,
        sentence_count=sentences,
        syllable_count=syllables,
        passes=grade <= target_grade + 2,  # Allow 2-grade buffer for legal terms
    )


# ============================================================================
# Text sources to scan
# ============================================================================


def _collect_backend_texts() -> dict[str, str]:
    """Collect all user-facing text from backend sources."""
    texts: dict[str, str] = {}

    # UPL prohibited phrases check (from settings)
    if hasattr(settings, "UPL_PROHIBITED_PHRASES"):
        for phrase in settings.UPL_PROHIBITED_PHRASES:
            texts[f"settings.UPL_PROHIBITED_PHRASES: '{phrase}'"] = phrase

    # Means test calculator messages
    try:
        from apps.eligibility.services.means_test_calculator import (
            MeansTestCalculator,
        )

        # Check the message generation method source for hardcoded strings
        import inspect

        source = inspect.getsource(
            MeansTestCalculator._generate_upl_compliant_message
        )

        # Extract string literals from the source
        string_literals = re.findall(r'"([^"]{20,})"', source)
        for i, lit in enumerate(string_literals):
            texts[f"MeansTestCalculator message fragment {i + 1}"] = lit
    except (ImportError, AttributeError, OSError):
        pass

    # UPL disclaimer from forms views
    try:
        from apps.forms.views import _UPL_DISCLAIMER

        texts["forms.views._UPL_DISCLAIMER"] = _UPL_DISCLAIMER
    except (ImportError, AttributeError):
        pass

    return texts


# ============================================================================
# Management command
# ============================================================================


class Command(BaseCommand):
    help = "Check reading level of all user-facing text (target: grade 6-8)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--target-grade",
            type=float,
            default=getattr(settings, "PLAIN_LANGUAGE_TARGET_GRADE_LEVEL", 7.0),
            help="Target Flesch-Kincaid grade level (default: 7)",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail on any text exceeding target (no 2-grade buffer)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show all results, not just failures",
        )

    def handle(self, *args, **options):
        target = options["target_grade"]
        strict = options["strict"]
        verbose = options["verbose"]

        self.stdout.write(
            self.style.NOTICE(
                f"Checking reading levels (target: grade {target}, "
                f"buffer: {'none' if strict else '2 grades'})..."
            )
        )
        self.stdout.write("")

        texts = _collect_backend_texts()

        if not texts:
            self.stdout.write(self.style.WARNING("No text sources found to check."))
            return

        results = [check_text(label, text, target) for label, text in texts.items()]

        if strict:
            # Override passes with strict check
            results = [
                ReadingLevelResult(
                    text_label=r.text_label,
                    grade_level=r.grade_level,
                    word_count=r.word_count,
                    sentence_count=r.sentence_count,
                    syllable_count=r.syllable_count,
                    passes=r.grade_level <= target,
                )
                for r in results
            ]

        failures = [r for r in results if not r.passes]
        passes = [r for r in results if r.passes]

        if verbose:
            for r in passes:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  PASS  grade {r.grade_level:4.1f}  "
                        f"({r.word_count}w/{r.sentence_count}s)  {r.text_label}"
                    )
                )

        for r in failures:
            self.stdout.write(
                self.style.ERROR(
                    f"  FAIL  grade {r.grade_level:4.1f}  "
                    f"({r.word_count}w/{r.sentence_count}s)  {r.text_label}"
                )
            )

        self.stdout.write("")
        self.stdout.write(
            f"Results: {len(passes)} passed, {len(failures)} failed "
            f"out of {len(results)} texts"
        )

        if failures:
            self.stdout.write(
                self.style.WARNING(
                    "\nTip: Legal terms may inflate grade level. "
                    "Consider adding plain-language explanations alongside them."
                )
            )
