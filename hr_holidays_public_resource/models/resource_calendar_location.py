# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.fields import Domain

SYNC_TRIGGER_FIELDS = {"active", "company_id", "public_holiday_line_ids"}


class ResourceCalendarLocation(models.Model):
    """A place of work, as far as public holidays are concerned.

    The standard work location carries an address and describes where
    somebody physically sits; public holidays only need a label to assign
    days by -- the Catholic municipalities of Bavaria, one plant, one shop.
    Every employee is assigned one, and a public holiday line names the
    locations it applies to.
    """

    _name = "resource.calendar.location"
    _description = "Public Holiday Location"
    _order = "name"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company",
        help="Leave empty for a location shared by every company.",
    )
    active = fields.Boolean(default=True)
    public_holiday_line_ids = fields.Many2many(
        "calendar.public.holiday.line",
        "calendar_public_holiday_line_calendar_location_rel",
        "location_id",
        "line_id",
        string="Public Holidays",
        help="Public holidays everybody working at this location gets, on "
        "top of the nationwide ones.",
    )
    public_holiday_overview_line_ids = fields.Many2many(
        "calendar.public.holiday.line",
        string="Public Holiday Overview",
        compute="_compute_public_holiday_overview_line_ids",
        help="Every public holiday somebody working at this location gets: "
        "the nationwide ones and the ones assigned to the location directly.",
    )

    @api.depends("company_id.country_id", "public_holiday_line_ids")
    def _compute_public_holiday_overview_line_ids(self):
        line_model = self.env["calendar.public.holiday.line"]
        # The always-true leaf keeps the no-search-all check quiet.
        lines = line_model.search([("id", "!=", 0)])
        nationwide = lines.filtered(lambda line: not line._has_public_holiday_scope())
        for location in self:
            reachable = nationwide | location.public_holiday_line_ids
            # Mirrors `resource.calendar._matches_public_holiday_country`: an
            # unknown company country cannot rule a holiday calendar out.
            country = location.company_id.country_id
            if country:
                reachable = reachable.filtered(
                    lambda line, country=country: (
                        not line.public_holiday_id.country_id
                        or line.public_holiday_id.country_id == country
                    )
                )
            location.public_holiday_overview_line_ids = reachable

    def _get_assigned_employees(self):
        """Everybody assigned here under any of their contracts."""
        return (
            self.env["hr.employee"]
            .sudo()
            .search(Domain("version_ids.resource_calendar_location_id", "in", self.ids))
        )

    def write(self, vals):
        res = super().write(vals)
        if SYNC_TRIGGER_FIELDS.intersection(vals):
            # The public holidays of everybody working here change with the
            # assigned holidays, the company, or the location going away.
            # Writing the assignment from this side never touches
            # `calendar.public.holiday.line.write`, so the line-side trigger
            # cannot see it.
            self._get_assigned_employees()._trigger_public_holiday_resync()
        return res
