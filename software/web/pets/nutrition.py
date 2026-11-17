"""Calculo de racion con base cientifica.

RER = 70 x peso_kg^0.75  (kcal en reposo)
MER = RER x factor       (kcal de mantenimiento)
gramos_dia = MER / kcal_por_gramo del alimento
"""
from __future__ import annotations

from dataclasses import dataclass

# Factores de mantenimiento. Fuente: guias de nutricion veterinaria (WSAVA/AAHA).
# El etologo del equipo valida estos valores antes de usarlos en produccion.
FACTORS = {
    "cat": {"adult_neutered": 1.2, "adult_intact": 1.4, "senior": 1.1, "weight_loss": 0.8},
    "dog": {"adult_neutered": 1.6, "adult_intact": 1.8, "active": 2.0, "senior": 1.4, "weight_loss": 1.0},
}

MIN_GRAMS = 5.0
MAX_DAILY_RATIO = 2.0


@dataclass(frozen=True)
class Ration:
    rer_kcal: float
    mer_kcal: float
    grams_per_day: float
    grams_per_meal: tuple[float, ...]
    factor: float


def resting_energy(weight_kg: float) -> float:
    if weight_kg <= 0:
        raise ValueError("El peso debe ser mayor que cero")
    return 70 * (weight_kg ** 0.75)


def maintenance_factor(species: str, profile: str = "adult_neutered") -> float:
    table = FACTORS.get(species)
    if not table:
        raise ValueError(f"Especie no soportada: {species}")
    return table.get(profile, table["adult_neutered"])


def grams_per_day(mer_kcal: float, kcal_per_gram: float) -> float:
    if kcal_per_gram <= 0:
        raise ValueError("Las kcal por gramo deben ser mayores que cero")
    return mer_kcal / kcal_per_gram


def split_in_meals(total_grams: float, meals: int) -> tuple[float, ...]:
    """Reparte sin perder gramos: el residuo va a la primera comida."""
    if meals < 1:
        raise ValueError("Debe haber al menos una comida")
    base = round(total_grams / meals, 1)
    portions = [base] * meals
    portions[0] = round(total_grams - base * (meals - 1), 1)
    return tuple(portions)


def compute_ration(
    *,
    species: str,
    weight_kg: float,
    kcal_per_gram: float = 3.6,
    profile: str = "adult_neutered",
    meals: int = 2,
) -> Ration:
    factor = maintenance_factor(species, profile)
    rer = resting_energy(weight_kg)
    mer = rer * factor
    daily = grams_per_day(mer, kcal_per_gram)
    return Ration(
        rer_kcal=round(rer, 1),
        mer_kcal=round(mer, 1),
        grams_per_day=round(daily, 1),
        grams_per_meal=split_in_meals(daily, meals),
        factor=factor,
    )


def adjust_for_leftover(planned_grams: float, leftover_grams: float) -> float:
    """Descuenta lo que quedo en el plato de la siguiente porcion del dia."""
    if leftover_grams <= 0:
        return round(planned_grams, 1)
    remaining = planned_grams - leftover_grams
    return round(max(MIN_GRAMS, remaining), 1)


def classify_intake(served: float, eaten: float) -> str:
    if served <= 0:
        return "none"
    ratio = eaten / served
    if ratio >= 0.9:
        return "ate"
    if ratio >= 0.3:
        return "partial"
    return "none"


def leftover_severity(leftover: float, served: float) -> str:
    """0 = sin sobrante, 1 = aviso, 2 = limpiar el plato."""
    if served <= 0 or leftover <= 0:
        return "none"
    ratio = leftover / served
    if ratio >= 0.5:
        return "clean"
    if ratio >= 0.2:
        return "warning"
    return "none"
