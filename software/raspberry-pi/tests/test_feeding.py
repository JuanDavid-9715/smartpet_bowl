import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import feeding  # noqa: E402


def test_resting_energy():
    assert feeding.resting_energy(10) == pytest.approx(393.6, abs=0.5)


def test_daily_grams_cat():
    assert feeding.daily_grams("cat", 10, 3.6, "adult_neutered") == pytest.approx(131.2, abs=0.2)


def test_daily_grams_dog():
    assert feeding.daily_grams("dog", 31, 3.6, "adult_neutered") == pytest.approx(408.7, abs=0.3)


def test_rejects_zero_weight():
    with pytest.raises(ValueError):
        feeding.resting_energy(0)


def test_rejects_unknown_species():
    with pytest.raises(ValueError):
        feeding.daily_grams("hamster", 1.0)


def test_rejects_zero_kcal():
    with pytest.raises(ValueError):
        feeding.daily_grams("cat", 4.0, 0)


def test_leftover_reduces_next_portion():
    assert feeding.adjust_for_leftover(65.0, 6.5) == pytest.approx(58.5)


def test_leftover_never_goes_below_minimum():
    assert feeding.adjust_for_leftover(20.0, 19.0) == feeding.MIN_GRAMS


def test_no_leftover_keeps_portion():
    assert feeding.adjust_for_leftover(65.0, 0) == 65.0


@pytest.mark.parametrize(
    "served,eaten,expected",
    [(100, 95, "ate"), (100, 90, "ate"), (100, 50, "partial"), (100, 10, "none"), (0, 0, "none")],
)
def test_classify_intake(served, eaten, expected):
    assert feeding.classify_intake(served, eaten) == expected


def test_session_computes_eaten_and_status():
    session = feeding.Session(pet="Jiru", planned=65, served=65, leftover=5)
    assert session.eaten == 60
    assert session.status == "ate"


def test_session_partial_when_leftover_is_high():
    session = feeding.Session(pet="Jiru", planned=65, served=65, leftover=7)
    assert session.eaten == 58
    assert session.status == "partial"
