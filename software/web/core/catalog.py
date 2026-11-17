"""Precios y planes en un solo lugar. Si cambia un precio, cambia aqui."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    slug: str
    name: str
    summary: str
    price_cop: int
    note: str


@dataclass(frozen=True)
class Plan:
    slug: str
    name: str
    price_cop: int
    period: str
    summary: str
    features: tuple[str, ...]
    featured: bool = False


FEEDER = Product(
    slug="comedero",
    name="Comedero",
    summary="Reconoce a cada mascota por la cara y el tamano, sirve su racion al gramo y te avisa si no comio.",
    price_cop=380_000,
    note="Pago unico. Sin mensualidad.",
)

SERVER = Product(
    slug="servidor",
    name="Servidor",
    summary="La misma aplicacion corriendo en tu casa. Tus datos no salen de tu red.",
    price_cop=620_000,
    note="Pago unico. Incluye el plan Local.",
)


@dataclass(frozen=True)
class Bundle:
    slug: str
    name: str
    contents: str
    price_cop: int
    before_cop: int


BUNDLES = (
    Bundle("comedero-servidor", "Comedero + servidor", "Los dos equipos.", 900_000, 1_000_000),
    Bundle("dos-comederos", "Dos comederos", "Una racion por mascota.", 680_000, 760_000),
    Bundle("dos-comederos-servidor", "Dos comederos + servidor", "El sistema completo.", 1_240_000, 1_380_000),
)

PLANS = (
    Plan(
        slug="hogar", name="Hogar", price_cop=25_000, period="al mes",
        summary="Para una mascota que come todos los dias.",
        features=("1 comedero", "Hasta 2 mascotas", "Historial de 30 dias", "Alertas en el celular"),
    ),
    Plan(
        slug="multi", name="Multi", price_cop=35_000, period="al mes",
        summary="Para casas con mas de una mascota.",
        features=("Hasta 4 comederos", "Hasta 4 mascotas", "Historial ilimitado", "Soporte prioritario"),
        featured=True,
    ),
    Plan(
        slug="local", name="Local", price_cop=0, period="sin mensualidad",
        summary="El servicio corre en tu propio servidor.",
        features=("Requiere el servidor", "Sin registro ni cuenta", "Los datos no salen de tu red", "Codigo abierto"),
    ),
)

CHECKS = (
    ("Obligatorio", "El comedero", "Es el aparato que sirve la comida. Sin esto no hay servicio.", FEEDER),
    ("Opcional", "El servidor", "Solo si quieres tus datos en casa. Si no, el servicio vive en la nube.", SERVER),
)


def cop(value: int) -> str:
    return f"COP {value:,.0f}".replace(",", ".")
