# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def _find_state_region(env, state, company):
    """The region standing for ``state``, if the upgrade created one.

    ``calendar_public_holiday`` turns the states its lines used to be scoped
    to into shared regions named after the state and carrying its country.
    A work location whose address lies in such a state belongs to that
    region, so that the people working there keep the public holidays of
    their region.
    """
    if not state:
        return env["calendar.public.holiday.region"]
    return env["calendar.public.holiday.region"].search(
        [
            ("name", "=", state.name),
            ("country_id", "=", state.country_id.id),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", company.id),
        ],
        order="company_id, id",
        limit=1,
    )


def create_regions_from_work_locations(env):
    """Bootstrap the public holiday regions from the work locations.

    Every work location without a public holiday region gets one: the region
    standing for the state of its address where the upgrade built one,
    otherwise a region of its own, named after the work location, owned by
    its company and carrying the country of its address. The assignment of
    every employee follows from there, since the public holiday region of a
    version (contract) is derived from its work location.

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
    linked = 0
    for work_location in work_locations:
        company = work_location.company_id
        region = _find_state_region(env, work_location.address_id.state_id, company)
        if region:
            linked += 1
        else:
            country = work_location.address_id.country_id or company.country_id
            region = region_model.create(
                {
                    "name": work_location.name,
                    "company_id": company.id,
                    "country_id": country.id,
                    "active": work_location.active,
                }
            )
            created |= region
        work_location.public_holiday_region_id = region
    _logger.info(
        "hr_holidays_public: created %s public holiday region(s) for %s work "
        "location(s), linked %s to the region of their state",
        len(created),
        len(work_locations),
        linked,
    )
    return created


def post_init_hook(env):
    create_regions_from_work_locations(env)
