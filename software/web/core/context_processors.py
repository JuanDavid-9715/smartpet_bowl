from django.conf import settings

from . import catalog


def site(request):
    return {
        "deployment": settings.DEPLOYMENT,
        "is_local": settings.IS_LOCAL,
        "catalog_feeder": catalog.FEEDER,
        "catalog_server": catalog.SERVER,
    }
