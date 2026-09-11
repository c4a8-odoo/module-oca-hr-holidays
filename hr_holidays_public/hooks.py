# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def _find_state_region(env, state, companies):
    """The region standing for ``state``, if the upgrade created one.

    ``calendar_public_holiday`` turns the states its lines used to be scoped
    to into shared regions named after the state -- with the country code
    appended where two countries share a state name. A work location whose
    address lies in such a state belongs to that region, so that the people
    working there keep the public holidays of their region.
    """
    if not state:
        return env["calendar.public.holiday.region"]
    names = [state.name, f"{state.name} ({state.country_id.code})"]
    return env["calendar.public.holiday.region"].search(
        [
            ("name", "in", names),
            "|",
            ("company_id", "=", False),
            ("company_id", "in", companies.ids),
        ],
        order="company_id, id",
        limit=1,
    )


def create_regions_from_work_locations(env):
    """Bootstrap the public holiday regions from the work locations.

    Every work location without a public holiday region gets one: the region
    standing for the state of its address where the upgrade built one,
    otherwise one region per distinct **work address** -- work locations
    sharing an address describe the same place as far as public holidays
    are concerned. The assignment of every employee follows from there,
    since the public holiday region of a version (contract) is derived from
    its work location.

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
    for address in work_locations.address_id:
        siblings = work_locations.filtered(
            lambda work_location, address=address: (work_location.address_id == address)
        )
        companies = siblings.company_id
        region = _find_state_region(env, address.state_id, companies)
        if region:
            linked += len(siblings)
        else:
            region = region_model.create(
                {
                    # Named after the work location; the first one takes it
                    # when several share the address.
                    "name": siblings[0].name,
                    # A shared address across companies makes a shared region.
                    "company_id": companies.id if len(companies) == 1 else False,
                    "active": any(siblings.mapped("active")),
                }
            )
            created |= region
        siblings.write({"public_holiday_region_id": region.id})
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
