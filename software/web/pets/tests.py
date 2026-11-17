from datetime import date

import pytest
from django.contrib.auth import get_user_model

from pets import nutrition
from pets.models import MealTime, Pet


def test_rer_uses_metabolic_weight():
    assert nutrition.resting_energy(10) == pytest.approx(393.6, abs=0.5)


def test_ration_cat_10kg():
    ration = nutrition.compute_ration(species="cat", weight_kg=10)
    assert ration.grams_per_day == pytest.approx(131.3, abs=0.5)
    assert sum(ration.grams_per_meal) == pytest.approx(ration.grams_per_day, abs=0.1)


def test_ration_dog_31kg():
    ration = nutrition.compute_ration(species="dog", weight_kg=31)
    assert ration.grams_per_day == pytest.approx(408.3, abs=1.0)


def test_split_keeps_total():
    portions = nutrition.split_in_meals(131.2, 3)
    assert len(portions) == 3
    assert pytest.approx(sum(portions), abs=0.05) == 131.2


def test_leftover_reduces_next_portion():
    assert nutrition.adjust_for_leftover(65, 6.5) == pytest.approx(58.5)


def test_leftover_has_floor():
    assert nutrition.adjust_for_leftover(10, 9.5) == nutrition.MIN_GRAMS


@pytest.mark.parametrize("leftover,expected", [(0, "none"), (5, "none"), (20, "warning"), (50, "clean")])
def test_leftover_severity(leftover, expected):
    assert nutrition.leftover_severity(leftover, 100) == expected


@pytest.mark.django_db
def test_pet_suggests_ration_and_schedule():
    User = get_user_model()
    user = User.objects.create_user(username="t@t.co", email="t@t.co", password="x")
    pet = Pet.objects.create(
        owner=user, name="Jiru", species="cat", weight_kg=10,
        birth_date=date(2021, 5, 12), meals_per_day=2,
    )
    ration = pet.suggested_ration()
    assert ration.grams_per_day > 0
    pet.ensure_schedule()
    assert MealTime.objects.filter(pet=pet).count() == 2
