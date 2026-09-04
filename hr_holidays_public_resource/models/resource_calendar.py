# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.fields import Domain


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    def _get_public_holiday_employees(self):
        """Employees whose working time this schedule governs."""
        self.ensure_one()
        return self.env["hr.employee"].search([("resource_calendar_id", "=", self.id)])

    @api.depends("public_holiday_employee_sync")
    def _compute_public_holiday_overview_line_ids(self):
        """Also count the regional days the schedule's employees get.

        The nationwide reach comes from ``calendar_public_holiday_resource``;
        a regional or location-scoped public holiday reaches the schedule
        through the people on it, which only this module can resolve. The
        employee entries are gated by *Apply Employee Public Holidays*, so a
        schedule opting out keeps the nationwide overview only.
        """
        res = super()._compute_public_holiday_overview_line_ids()
        line_model = self.env["calendar.public.holiday.line"]
        for calendar in self.filtered("public_holiday_employee_sync"):
            employees = calendar.sudo()._get_public_holiday_employees()
            locations = employees.resource_calendar_location_id
            states = employees.work_location_id.address_id.state_id
            if not locations and not states:
                continue
            scoped = line_model.search(
                Domain.OR(
                    [
                        Domain("location_ids", "in", locations.ids),
                        Domain("state_ids", "in", states.ids),
                    ]
                )
            )
            calendar.public_holiday_overview_line_ids |= (
                calendar._filter_public_holiday_overview_lines(scoped)
            )
        return res
