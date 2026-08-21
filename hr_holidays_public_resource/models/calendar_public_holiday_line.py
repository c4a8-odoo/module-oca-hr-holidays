# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class CalendarPublicHolidayLine(models.Model):
    _inherit = "calendar.public.holiday.line"

    location_ids = fields.Many2many(
        "resource.calendar.location",
        "calendar_public_holiday_line_calendar_location_rel",
        "line_id",
        "location_id",
        string="Locations",
        help="Employees assigned to one of these locations get this public "
        "holiday, in addition to anybody matched by the related states. For "
        "public holidays observed only in some municipalities, which no "
        "state can express.",
    )

    def _has_public_holiday_scope(self):
        return super()._has_public_holiday_scope() or bool(self.location_ids)

    @api.model
    def _get_public_holiday_sync_trigger_fields(self):
        return super()._get_public_holiday_sync_trigger_fields() | {"location_ids"}

    def _public_holiday_scope_description(self):
        self.ensure_one()
        names = (
            self.state_ids.mapped("name")
            + self.location_ids.mapped("name")
            + self.additional_resource_calendar_ids.mapped("name")
        )
        return self.env._(
            "nobody works in %s (a regional public holiday is given to the "
            "people whose work location is in one of its regions or who are "
            "assigned to one of its locations)",
            ", ".join(names),
        )

    def _get_domain_check_date_state_one(self):
        # A line scoped to locations is not a nationwide duplicate of a real
        # nationwide line on the same date.
        return super()._get_domain_check_date_state_one() + [
            ("location_ids", "=", False)
        ]

    def _check_date_state_one(self):
        res = super()._check_date_state_one()
        if self.location_ids:
            others = self.search(
                [
                    ("date", "=", self.date),
                    ("public_holiday_id", "=", self.public_holiday_id.id),
                    ("location_ids", "!=", False),
                    ("id", "!=", self.id),
                ]
            )
            for other in others:
                if self.location_ids & other.location_ids:
                    raise ValidationError(
                        self.env._(
                            "You can't create duplicate public holiday per "
                            "date %s and one of the locations.",
                            self.date,
                        )
                    )
        return res

    @api.constrains("date", "location_ids")
    def _check_date_location(self):
        # Also re-runs the nationwide-duplicate check: clearing the locations
        # turns a line nationwide, which `_check_date_state` does not see
        # because the states did not change.
        for line in self:
            line._check_date_state_one()

    def _get_public_holiday_resource_targets(self, calendars):
        """Resolve regional public holidays to the people they are for.

        A working schedule is one scope, so generating a regional public
        holiday on it would give it to everybody sharing the schedule. It is
        generated for the resource of each employee working in one of its
        regions instead, which lets colleagues on one schedule keep different
        regions.

        A line reaches the union of what its two scopes match: everybody
        assigned to one of its locations, and everybody whose work location
        lies in one of its related states. The direct assignment covers
        public holidays observed only in some municipalities; the region is
        always the one of the **work location** of the employee -- where the
        work is actually done, which is what a public holiday follows. The
        work address of the employee record is often the company address and
        says nothing about the region.

        Both the location and the schedule are taken from the version
        (contract) valid on the day of the line, so a contract change in
        October moves the October holidays without touching the March ones.
        A day no contract covers is given to nobody.
        """
        targets = super()._get_public_holiday_resource_targets(calendars)
        scoped = self.filtered(
            lambda line: line.active and (line.state_ids or line.location_ids)
        )
        if not scoped:
            return targets
        # Matched through the versions rather than the current values, so a
        # location somebody works at only under a past or future contract is
        # found as well.
        employees = (
            self.env["hr.employee"]
            .sudo()
            .search(
                Domain.AND(
                    [
                        Domain("version_ids.resource_calendar_id", "in", calendars.ids),
                        Domain("resource_id", "!=", False),
                        Domain.OR(
                            [
                                Domain(
                                    "version_ids.resource_calendar_location_id",
                                    "in",
                                    scoped.location_ids.ids,
                                ),
                                Domain(
                                    "version_ids.work_location_id.address_id.state_id",
                                    "in",
                                    scoped.state_ids.ids,
                                ),
                            ]
                        ),
                    ]
                )
            )
        )
        for employee in employees:
            company = employee.company_id
            if not company:
                continue
            for line in scoped:
                if not employee._is_in_contract(line.date):
                    continue
                version = employee._get_version(line.date)
                calendar = version.resource_calendar_id
                # A calendar outside the requested subset stays untouched by
                # this run and would collide with its existing mirror.
                if not calendar or calendar not in calendars:
                    continue
                location = version.resource_calendar_location_id
                state = version.work_location_id.address_id.state_id
                matches_location = location in line.location_ids
                matches_state = bool(state) and state in line.state_ids
                if not (matches_location or matches_state):
                    continue
                if not calendar._matches_public_holiday_country(line, company):
                    continue
                targets.append((line, employee.resource_id, calendar, company))
        return targets
