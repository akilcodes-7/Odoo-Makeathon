from core.views import empty_state


def index(request):
    return empty_state(
        request,
        feature_label="Discounts and quotations",
        message="Offers and quotation tools are not available yet.",
        template_name="offers/empty_state.html",
    )
