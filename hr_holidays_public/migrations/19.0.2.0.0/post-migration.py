# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api

from odoo.addons.hr_holidays_public.hooks import create_regions_from_work_locations


def migrate(cr, version):
    # Public holidays follow the region of the employee from this version
    # on. Every work location is linked to the region of its state --
    # created by calendar_public_holiday from the former related states --
    # or given a region of its own, named after it, owned by its company and
    # carrying the country of its address, so that everybody keeps their
    # public holidays.
    env = api.Environment(cr, SUPERUSER_ID, {})
    create_regions_from_work_locations(env)
