"""Raciones y sobrantes. La misma formula que usa la web."""
from dataclasses import dataclass

FACTORS = {
    "cat": {"adult_neutered": 1.2, "adult_intact": 1.4, "senior": 1.1, "weight_loss": 0.8},
    "dog": {"adult_neutered": 1.6, "adult_intact": 1.8, "active": 2.0, "senior": 1.4, "weight_loss": 1.0},
}

MIN_GRAMS = 5.0


def resting_energy(weight_kg: float) -> float:
    if weight_kg <= 0:
        raise ValueError("El peso debe ser mayor que cero")
    return 70 * (weight_kg ** 0.75)


def daily_grams(species: str, weight_kg: float, kcal_per_gram: float = 3.6,
                profile: str = "adult_neutered") -> float:
    if kcal_per_gram <= 0:
        raise ValueError("Las kcal por gramo deben ser mayores que cero")
    if species not in FACTORS:
        raise ValueError(f"Especie no soportada: {species}")
    factor = FACTORS[species].get(profile, 1.2)
    return round(resting_energy(weight_kg) * factor / kcal_per_gram, 1)


def adjust_for_leftover(planned: float, leftover: float) -> float:
    if leftover <= 0:
        return round(planned, 1)
    return round(max(MIN_GRAMS, planned - leftover), 1)


def classify_intake(served: float, eaten: float) -> str:
    if served <= 0:
        return "none"
    ratio = eaten / served
    if ratio >= 0.9:
        return "ate"
    if ratio >= 0.3:
        return "partial"
    return "none"


@dataclass
class Session:
    """Una comida en curso."""
    pet: str
    planned: float
    served: float = 0.0
    leftover: float = 0.0
    confidence: float = 0.0

    @property
    def eaten(self) -> float:
        return round(max(0.0, self.served - self.leftover), 1)

    @property
    def status(self) -> str:
        return classify_intake(self.served, self.eaten)
