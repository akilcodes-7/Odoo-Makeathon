from core.views import empty_state


def index(request):
    return empty_state(
        request,
        feature_label="Invoices and payments",
        message="Invoice and payment management is not available yet.",
        template_name="finance/empty_state.html",
    )
