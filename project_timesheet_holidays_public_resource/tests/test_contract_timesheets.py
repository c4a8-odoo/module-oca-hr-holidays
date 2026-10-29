# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged

from .common import TestPublicResourceTimesheetCommon


@tagged("post_install", "-at_install")
class TestContractTimesheets(TestPublicResourceTimesheetCommon):
    """Public holiday timesheets follow the contract scope.

    A public holiday only concerns somebody employed on that day: no entry
    without a contract, and ending a contract removes the future entries
    beyond its end.
    """

    def _future_line(self):
        day = fields.Date.today() + timedelta(days=7)
        while day.weekday() != 0:
            day += timedelta(days=1)
        holiday = (
            self.holiday
            if day.year == self.year
            else self.holiday_model.create(
                {"year": day.year, "country_id": self.country.id}
            )
        )
        line = self.line_model.create(
            {"name": "Future national", "date": day, "public_holiday_id": holiday.id}
        )
        return line, day

    def test_no_contract_no_timesheet(self):
        casual = self.env["hr.employee"].create(
            {
                "name": "Emp Casual TS",
                "company_id": self.company.id,
                "resource_calendar_id": self.calendar.id,
            }
        )
        line, day = self._future_line()
        self.assertFalse(
            self._lines_for(casual, day),
            "no contract means no public holiday timesheet",
        )
        self.assertTrue(self._lines_for(self.employee, day))

    def test_contract_end_removes_the_future_entries(self):
        line, day = self._future_line()
        self.assertTrue(self._lines_for(self.employee, day))
        self.employee.version_id.contract_date_end = fields.Date.today()
        self.assertFalse(
            self._lines_for(self.employee, day),
            "the day lies beyond the contract end",
        )
        # Extending the contract brings the entry back.
        self.employee.version_id.contract_date_end = day + timedelta(days=30)
        self.assertTrue(self._lines_for(self.employee, day))

    def test_contract_start_rebuilds_the_entries_once(self):
        """Setting the contract start date books the days, in one rebuild.

        Standard propagates the contract dates through a nested version write
        under ``sync_contract_dates``; the entries used to be created,
        deleted and created again within that single write.
        """
        casual = self.env["hr.employee"].create(
            {
                "name": "Emp Casual Start",
                "company_id": self.company.id,
                "resource_calendar_id": self.calendar.id,
            }
        )
        line, day = self._future_line()
        self.assertFalse(self._lines_for(casual, day))
        Employee = self.registry["hr.employee"]
        original = Employee._refresh_future_public_holiday_timesheets
        refreshed = []

        def counting(employees):
            refreshed.append(employees.ids)
            return original(employees)

        self.patch(Employee, "_refresh_future_public_holiday_timesheets", counting)
        casual.contract_date_start = fields.Date.today() - timedelta(days=30)
        self.assertEqual(
            len(self._lines_for(casual, day)),
            1,
            "the contract start date books the public holiday once",
        )
        self.assertEqual(
            refreshed,
            [casual.ids],
            "the nested contract date propagation must not rebuild as well",
        )
