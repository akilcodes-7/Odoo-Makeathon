from core.views import empty_state


def index(request):
    return empty_state(
        request,
        feature_label="Overview",
        message="Dashboard information is unavailable until real subscription and billing records exist.",
        template_name="insights/empty_state.html",
    )
