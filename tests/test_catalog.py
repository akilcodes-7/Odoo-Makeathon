from datetime import date, timedelta

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from catalog.forms import PlanForm, ProductForm, TaxForm, VariantForm
from core.models import Plan, Product, ProductVariant, Tax


class CatalogFormTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="Managed hosting", type=Product.Type.SERVICE, sales_price_paise=56000, cost_price_paise=12000)

    def test_rupee_values_are_converted_to_integer_paise(self):
        form = ProductForm({"name": "Support", "type": "SERVICE", "sales_price_paise": "560.00", "cost_price_paise": "125.50", "notes": ""})
        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertEqual(product.sales_price_paise, 56000)
        self.assertEqual(product.cost_price_paise, 12550)

    def test_money_rejects_more_than_two_decimals_and_negative_price(self):
        for amount in ("12.345", "-0.01"):
            form = ProductForm({"name": "Invalid", "type": "SERVICE", "sales_price_paise": amount, "cost_price_paise": "0", "notes": ""})
            self.assertFalse(form.is_valid())
            self.assertIn("sales_price_paise", form.errors)

    def test_variant_must_belong_to_selected_product_and_effective_price_is_nonnegative(self):
        other = Product.objects.create(name="Other", type=Product.Type.ADDON, sales_price_paise=100, cost_price_paise=0)
        form = VariantForm({"product": str(other.pk), "attribute_name": "Tier", "attribute_value": "Plus", "extra_price_paise": "-2.00"})
        self.assertFalse(form.is_valid())
        self.assertIn("extra_price_paise", form.errors)
        form = VariantForm({"product": str(self.product.pk), "attribute_name": "Seats", "attribute_value": "10", "extra_price_paise": "560.00"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().extra_price_paise, 56000)

    def test_plan_rejects_invalid_dates_and_zero_quantity(self):
        form = PlanForm({"name": "Monthly", "primary_product": self.product.pk, "price_paise": "560.00", "period": "MONTHLY", "min_quantity": "0", "available_from": "2026-11-02", "available_until": "2026-11-01", "auto_close": "", "closable": "on", "pausable": "", "renewable": "on"})
        self.assertFalse(form.is_valid())
        self.assertIn("min_quantity", form.errors)
        self.assertIn("available_until", form.errors)

    def test_tax_percent_converts_to_basis_points(self):
        form = TaxForm({"name": "GST", "rate_percent": "18.00"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().rate_bps, 1800)
        self.assertFalse(TaxForm({"name": "Too high", "rate_percent": "100.01"}).is_valid())


class CatalogAccessAndPersistenceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin@example.com", "x", role=User.Role.ADMIN)
        self.staff = User.objects.create_user("staff@example.com", "x", role=User.Role.STAFF)
        self.customer = User.objects.create_user("customer@example.com", "x", role=User.Role.CUSTOMER)
        self.product = Product.objects.create(name="Public service", type=Product.Type.SERVICE, sales_price_paise=8900, cost_price_paise=2500)
        self.plan = Plan.objects.create(name="Monthly", primary_product=self.product, price_paise=8900, period=Plan.Period.MONTHLY, min_quantity=1, available_from=date.today() - timedelta(days=1))

    def test_admin_only_mutations_and_staff_catalog_access(self):
        client = Client()
        client.force_login(self.staff)
        self.assertEqual(client.get(reverse("catalog:products")).status_code, 200)
        response = client.post(reverse("catalog:product_create"), {"name": "Blocked", "type": "SERVICE", "sales_price_paise": "1.00", "cost_price_paise": "0", "notes": ""})
        self.assertEqual(response.status_code, 403)
        client.force_login(self.customer)
        self.assertEqual(client.get(reverse("catalog:products")).status_code, 403)

    def test_customer_sees_only_current_eligible_plans_without_cost(self):
        hidden = Plan.objects.create(name="Future", primary_product=self.product, price_paise=100, period=Plan.Period.MONTHLY, available_from=date.today() + timedelta(days=5))
        client = Client()
        client.force_login(self.customer)
        response = client.get(reverse("catalog:plans"))
        self.assertContains(response, "Monthly")
        self.assertNotContains(response, "Future")
        self.assertNotContains(response, "2500")

    def test_archiving_keeps_referenced_rows_but_hides_them_from_active_catalog(self):
        client = Client()
        client.force_login(self.admin)
        self.assertEqual(client.post(reverse("catalog:product_archive", args=[self.product.pk])).status_code, 302)
        self.product.refresh_from_db()
        self.plan.refresh_from_db()
        self.assertFalse(self.product.is_active)
        self.assertTrue(self.plan.is_active)
        self.assertTrue(Plan.objects.filter(pk=self.plan.pk).exists())

    def test_variant_create_endpoint_is_scoped_to_product_in_url(self):
        other = Product.objects.create(name="Other product", type=Product.Type.ADDON, sales_price_paise=1000, cost_price_paise=200)
        client = Client()
        client.force_login(self.admin)
        response = client.post(reverse("catalog:variant_create", args=[self.product.pk]), {
            "product": other.pk,
            "attribute_name": "Tier",
            "attribute_value": "Plus",
            "extra_price_paise": "5.00",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProductVariant.objects.exists())

    def test_plan_survives_process_style_reload_with_exact_paise(self):
        self.assertEqual(Plan.objects.get(pk=self.plan.pk).price_paise, 8900)
