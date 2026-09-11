# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo.addons.calendar_public_holiday.hooks import (
    assign_regions_from_legacy_states,
)

_logger = logging.getLogger(__name__)


def create_regions_from_work_locations(env):
    """Bootstrap the public holiday regions from the work locations.

    Every work location without a public holiday region gets one of its
    own, named after the work location, owned by its company and carrying
    the country and state of its address. The assignment of every employee
    follows from there, since the public holiday region of a version
    (contract) is derived from its work location.

    Idempotent: work locations already carrying a region are left alone.
    Returns the regions created.
    """
    region_model = env["calendar.public.holiday.region"]
    work_locations = (
        env["hr.work.location"]
        .with_context(active_test=False)
        .search([("public_holiday_region_id", "=", False)])
    )
    created = region_model.browse()
    for work_location in work_locations:
        address = work_location.address_id
        company = work_location.company_id
        country = (
            address.country_id or address.state_id.country_id or company.country_id
        )
        region = region_model.create(
            {
                "name": work_location.name,
                "company_id": company.id,
                "country_id": country.id,
                "state_id": address.state_id.id,
                "active": work_location.active,
            }
        )
        created |= region
        work_location.public_holiday_region_id = region
    _logger.info(
        "hr_holidays_public: created %s public holiday region(s) for %s work "
        "location(s)",
        len(created),
        len(work_locations),
    )
    return created


def bootstrap_regions(env):
    """Build the regions and hand the former state-scoped lines to them.

    The regions carry the state of their work address, so the public
    holidays that used to be scoped to a state now reach the regions lying
    in it; a line whose states no work location lies in stays disabled.
    """
    created = create_regions_from_work_locations(env)
    assign_regions_from_legacy_states(env)
    return created


def post_init_hook(env):
    bootstrap_regions(env)
