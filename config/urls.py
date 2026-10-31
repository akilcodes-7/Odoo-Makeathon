from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("insights.urls", namespace="insights")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("team/", include("core.team_urls", namespace="team")),
    path("core/", include("core.urls", namespace="core")),
    path("catalog/", include("catalog.urls", namespace="catalog")),
    path("subscriptions/", include("subscriptions.urls", namespace="subscriptions")),
    path("customers/", include("core.customer_urls", namespace="customers")),
    path("offers/", include("offers.urls", namespace="offers")),
    path("invoices/", include("finance.delivery_urls", namespace="finance_delivery")),
    path("invoices/", include("finance.payment_urls", namespace="finance_payments")),
    path("invoices/", include("finance.urls", namespace="finance")),
    path("billing/", include("core.billing_urls", namespace="billing")),
    path("portal/", include("portal.urls", namespace="portal")),
]
