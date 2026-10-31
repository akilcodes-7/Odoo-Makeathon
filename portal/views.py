from core.views import empty_state


def index(request):
    return empty_state(
        request,
        feature_label="Customer portal",
        message="Customer subscriptions and invoices are not available yet.",
        template_name="portal/empty_state.html",
    )


def subscriptions_unavailable(request):
    return empty_state(
        request,
        feature_label="My subscriptions",
        message="Your subscriptions are not available yet.",
        template_name="portal/empty_state.html",
    )


def invoices_unavailable(request):
    return empty_state(
        request,
        feature_label="My invoices",
        message="Your invoices are not available yet.",
        template_name="portal/empty_state.html",
    )


def profile_unavailable(request):
    return empty_state(
        request,
        feature_label="Profile",
        message="Profile management is not available yet.",
        template_name="portal/empty_state.html",
    )
