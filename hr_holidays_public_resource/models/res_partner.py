# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):
        res = super().write(vals)
        if "state_id" in vals or "country_id" in vals:
            # An address moving region moves the people working at it.
            employees = (
                self.env["hr.employee"]
                .sudo()
                .search([("work_location_id.address_id", "in", self.ids)])
            )
            employees._trigger_public_holiday_resync()
        return res
