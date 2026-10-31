from core.views import empty_state


def index(request):
    return empty_state(
        request,
        feature_label="Subscriptions",
        message="Subscription management is not available yet.",
        template_name="subscriptions/empty_state.html",
    )


def customers_unavailable(request):
    return empty_state(
        request,
        feature_label="Customers",
        message="Customer records are not available yet.",
        template_name="subscriptions/empty_state.html",
    )
