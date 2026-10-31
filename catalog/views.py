from core.views import empty_state


def index(request):
    return empty_state(
        request,
        feature_label="Products and plans",
        message="Catalog management is not available yet.",
        template_name="catalog/empty_state.html",
    )
