"""Database-only homepage totals. Run on a disposable Frappe test site."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from masters_association import website


class TestWebsiteStats(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.savepoint("website_stats_test")
		self.addCleanup(self._rollback)
		self.enqueue = self.enterContext(patch("frappe.enqueue"))
		self.provider_requests = self.enterContext(
			patch("requests.sessions.Session.request", side_effect=AssertionError("Homepage must not call providers"))
		)
		self.enterContext(patch.object(website, "today", return_value="2026-10-30"))
		self.suffix = frappe.generate_hash(length=10)
		self.baseline = website._get_home_stats()

	def _rollback(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="website_stats_test")

	def _account(self, suffix, approved=True):
		member = frappe.get_doc({
			"doctype": "Association Member",
			"name1": f"Website stats {suffix} {self.suffix}",
			"email": f"website-{suffix}-{self.suffix}@example.com",
			"mobile_no_whatsapp": "+919876543210",
			"district": "Thrissur",
			"gst": f"WEB-{suffix}-{self.suffix}",
			"membership_status": "Normal Member",
			"show_on_website": 0,
			"portal_enabled": 0,
		}).insert(ignore_permissions=True)
		if approved:
			member.db_set("application_status", "Approved")
		return frappe.get_doc({
			"doctype": "Solar API Account",
			"member": member.name,
			"provider": "Deye",
			"account_label": f"Website {suffix}",
			"enabled": 0,
		}).insert(ignore_permissions=True)

	def _station(self, account, suffix, **readings):
		return frappe.get_doc({
			"doctype": "Solar Station",
			"account": account.name,
			"external_id": f"website-{suffix}-{self.suffix}",
			"station_name": f"Website plant {suffix} {self.suffix}",
			"present": 1,
			"capacity_kw": 5,
			"production_date": "2026-10-30",
			"has_daily": 1,
			"has_monthly": 1,
			"has_total": 1,
			"daily_production_kwh": 10,
			"monthly_production_kwh": 100,
			"total_production_kwh": 1000,
			"last_production_fetch": "2026-10-30 09:00:00",
			**readings,
		}).insert(ignore_permissions=True)

	def _assert_increase(self, stats, field, expected):
		self.assertAlmostEqual((stats[field] or 0) - (self.baseline[field] or 0), expected, msg=field)

	def test_home_aggregates_all_approved_members_without_provider_calls(self):
		first = self._account("first")
		second = self._account("second")
		pending = self._account("pending", approved=False)
		station = self._station(first, "today")
		self._station(second, "yesterday", production_date="2026-10-29")
		self._station(second, "previous-month", production_date="2026-09-30")
		self._station(first, "removed", present=0)
		self._station(pending, "pending")
		self.enqueue.reset_mock()

		frappe.set_user("Guest")
		result = website.get_home_data()["stats"]
		for field, expected in {
			"member_count": 2,
			"station_count": 3,
			"capacity_kw": 15,
			"daily_production_kwh": 10,
			"daily_production_kwh_coverage": 1,
			"monthly_production_kwh": 200,
			"monthly_production_kwh_coverage": 2,
			"total_production_kwh": 3000,
			"total_production_kwh_coverage": 3,
		}.items():
			self._assert_increase(result, field, expected)
		self.assertEqual(result["production_date"], "2026-10-30")
		self.assertEqual(set(result), set(self.baseline))
		self.assertNotIn(station.name, frappe.as_json(result))
		self.assertEqual(frappe.db.get_value("Solar Station", station.name, "daily_production_kwh"), 10)
		self.provider_requests.assert_not_called()
		self.enqueue.assert_not_called()

	def test_missing_readings_are_excluded_but_measured_zero_counts(self):
		account = self._account("missing")
		self._station(account, "missing", has_daily=0, has_monthly=0, has_total=0)
		self._station(account, "zero", daily_production_kwh=0, monthly_production_kwh=0, total_production_kwh=0)
		frappe.set_user("Guest")
		stats = website._get_home_stats()
		for field in ("daily_production_kwh", "monthly_production_kwh", "total_production_kwh"):
			self._assert_increase(stats, field, 0)
			self._assert_increase(stats, field + "_coverage", 1)

	def test_saved_production_changes_are_visible_without_another_refresh(self):
		account = self._account("updated")
		station = self._station(account, "updated")
		before = website._get_home_stats()
		# Simulate a scheduled/manual production job writing a new snapshot.
		frappe.db.set_value("Solar Station", station.name, "daily_production_kwh", 25)
		frappe.set_user("Guest")
		after = website._get_home_stats()
		self.assertEqual(after["daily_production_kwh"] - before["daily_production_kwh"], 15)
		self.provider_requests.assert_not_called()
