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


@dataclass(frozen=True)
class CartItem:
    slug: str
    title: str
    kind: str            # "once" | "monthly"
    price_cop: int
    summary: str
    note: str
    lines: tuple[tuple[str, int], ...] = ()
    before_cop: int | None = None

    @property
    def is_subscription(self) -> bool:
        return self.kind == "monthly"

    @property
    def cta(self) -> str:
        return "Suscribirme" if self.is_subscription else "Pagar"

    @property
    def period(self) -> str:
        return "al mes" if self.is_subscription else "pago unico"


def _item(slug: str, title: str, kind: str, price: int, summary: str, note: str,
          lines=(), before=None) -> CartItem:
    return CartItem(slug, title, kind, price, summary, note, tuple(lines), before)


ITEMS: dict[str, CartItem] = {
    "comedero": _item("comedero", "Comedero SmartPet Bowl", "once", FEEDER.price_cop,
                      FEEDER.summary, FEEDER.note, [("Comedero", FEEDER.price_cop)]),
    "servidor": _item("servidor", "Servidor local", "once", SERVER.price_cop,
                      SERVER.summary, SERVER.note, [("Servidor", SERVER.price_cop)]),
    "combo-comedero-servidor": _item(
        "combo-comedero-servidor", "Comedero + servidor", "once", 900_000,
        "Los dos equipos.", "Pago unico. Incluye el plan Local.",
        [("Comedero", FEEDER.price_cop), ("Servidor", SERVER.price_cop)], 1_000_000),
    "combo-dos-comederos": _item(
        "combo-dos-comederos", "Dos comederos", "once", 680_000,
        "Una racion por mascota.", "Pago unico.",
        [("Dos comederos", FEEDER.price_cop * 2)], 760_000),
    "combo-dos-comederos-servidor": _item(
        "combo-dos-comederos-servidor", "Dos comederos + servidor", "once", 1_240_000,
        "El sistema completo.", "Pago unico. Incluye el plan Local.",
        [("Dos comederos", FEEDER.price_cop * 2), ("Servidor", SERVER.price_cop)], 1_380_000),
}

for plan in PLANS:
    ITEMS[f"plan-{plan.slug}"] = _item(
        f"plan-{plan.slug}", f"Plan {plan.name}", "monthly", plan.price_cop,
        plan.summary, "Se cobra cada mes. Puedes cancelar cuando quieras.",
        [(f"Plan {plan.name}", plan.price_cop)])

DEFAULT_ITEM = "combo-comedero-servidor"


def resolve_item(slug: str | None) -> CartItem:
    return ITEMS.get((slug or "").strip(), ITEMS[DEFAULT_ITEM])
