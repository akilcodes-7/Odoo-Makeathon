from core.views import empty_state


def index(request):
    return empty_state(
        request,
        feature_label="Accounts",
        message="Sign-in and account management are not available yet.",
        template_name="accounts/empty_state.html",
    )


def login_unavailable(request):
    return empty_state(
        request,
        feature_label="Sign in",
        message="Authentication is not available yet.",
        template_name="accounts/empty_state.html",
    )
