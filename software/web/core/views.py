from django.shortcuts import render

from . import catalog


def landing(request):
    unread = 0
    if request.user.is_authenticated:
        unread = request.user.pets.filter(alerts__read_at__isnull=True).count()
    return render(request, "core/landing.html", {
        "plans": catalog.PLANS,
        "bundles": catalog.BUNDLES,
        "cop": catalog.cop,
        "unread": unread,
    })


def product(request):
    return render(request, "core/product.html", {
        "feeder": catalog.FEEDER,
        "server": catalog.SERVER,
        "bundles": catalog.BUNDLES,
        "cop": catalog.cop,
    })


def plans(request):
    return render(request, "core/plans.html", {"plans": catalog.PLANS, "cop": catalog.cop})


def open_source(request):
    return render(request, "core/open_source.html", {"server": catalog.SERVER, "cop": catalog.cop})


def checkout(request):
    item = catalog.resolve_item(request.GET.get("item"))
    discount = (item.before_cop - item.price_cop) if item.before_cop else 0
    return render(request, "core/checkout.html", {"item": item, "discount": discount, "cop": catalog.cop})


def checkout_done(request):
    item = catalog.resolve_item(request.POST.get("item") or request.GET.get("item"))
    return render(request, "core/checkout_done.html", {"item": item})
