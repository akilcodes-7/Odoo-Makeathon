from django.shortcuts import render


def empty_state(request, *, feature_label: str, message: str, template_name: str):
    """Render the shared, honest placeholder for an unwired feature area."""
    return render(
        request,
        template_name,
        {
            "page_title": feature_label,
            "feature_label": feature_label,
            "message": message,
            "is_feature_available": False,
        },
    )


def index(request):
    return empty_state(
        request,
        feature_label="Shared operations",
        message="Core workflows are not available yet.",
        template_name="core/empty_state.html",
    )


def customers_index(request):
    return empty_state(
        request,
        feature_label="Customers",
        message="Customer records are not available yet.",
        template_name="core/empty_state.html",
    )
