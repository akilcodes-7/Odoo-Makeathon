from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("insights.urls", namespace="insights")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("core/", include("core.urls", namespace="core")),
    path("catalog/", include("catalog.urls", namespace="catalog")),
    path("subscriptions/", include("subscriptions.urls", namespace="subscriptions")),
    path("customers/", include("core.customer_urls", namespace="customers")),
    path("offers/", include("offers.urls", namespace="offers")),
    path("invoices/", include("finance.urls", namespace="finance")),
    path("portal/", include("portal.urls", namespace="portal")),
]
