# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

SYNC_TRIGGER_FIELDS = {"resource_calendar_location_id", "active"}


class HrWorkLocation(models.Model):
    _inherit = "hr.work.location"

    resource_calendar_location_id = fields.Many2one(
        "resource.calendar.location",
        string="Public Holiday Location",
        help="The public holiday location standing for this work location. "
        "Everybody working here follows it: the assignment on the employee "
        "is derived from the work location of each version (contract). "
        "Installing the module builds one location per distinct work "
        "address and links every work location to it.",
    )

    def write(self, vals):
        res = super().write(vals)
        if SYNC_TRIGGER_FIELDS.intersection(vals):
            # Relinking a work location moves everybody working there to
            # another public holiday location; the derived field on the
            # versions recomputes without a write of its own, so nothing else
            # can see the change.
            employees = (
                self.env["hr.employee"]
                .sudo()
                .search([("version_ids.work_location_id", "in", self.ids)])
            )
            employees._trigger_public_holiday_resync()
        return res
