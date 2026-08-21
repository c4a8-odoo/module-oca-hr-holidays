# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import Command

_logger = logging.getLogger(__name__)


def create_locations_from_work_locations(env):
    """Bootstrap the public holiday locations from the work locations.

    One location is created per distinct **work address**: work locations
    sharing an address describe the same place as far as public holidays are
    concerned. Each work location is linked to the location built from its
    address; the assignment of every employee follows from there, since the
    public holiday location of a version (contract) is derived from its work
    location.

    Idempotent: work locations already carrying a location are left alone.
    """
    location_model = env["resource.calendar.location"]
    work_locations = (
        env["hr.work.location"]
        .with_context(active_test=False)
        .search([("resource_calendar_location_id", "=", False)])
    )
    created = location_model.browse()
    for address in work_locations.address_id:
        siblings = work_locations.filtered(
            lambda work_location, address=address: (work_location.address_id == address)
        )
        companies = siblings.company_id
        location = location_model.create(
            {
                # Named after the work location; the first one takes it when
                # several share the address.
                "name": siblings[0].name,
                # A shared address across companies makes a shared location.
                "company_id": companies.id if len(companies) == 1 else False,
                "active": any(siblings.mapped("active")),
            }
        )
        siblings.write({"resource_calendar_location_id": location.id})
        created |= location
    _logger.info(
        "hr_holidays_public_resource: created %s public holiday location(s) "
        "from %s work location(s)",
        len(created),
        len(work_locations),
    )
    return created


def seed_line_locations_from_states(env):
    """Assign each state-scoped line the locations lying in its states.

    A public holiday location has no geography of its own; its state is the
    one of the work address of the work location(s) it was built from. Every
    line with *Related States* is given the locations whose origin lies in
    one of them, which makes the configuration visible per location and lets
    a line be switched to purely location-based scoping by clearing its
    states.

    The states are kept: the two scopes are a union, so the seeding changes
    nothing about who gets which day until somebody edits the lines.

    Returns the number of lines that received at least one location.
    """
    lines = env["calendar.public.holiday.line"].search([("state_ids", "!=", False)])
    if not lines:
        return 0
    # Only active locations of active work locations: an archived one is
    # filtered out whenever the many2many is read, so linking it would be
    # invisible dead data.
    work_locations = env["hr.work.location"].search(
        [
            ("resource_calendar_location_id", "!=", False),
            ("resource_calendar_location_id.active", "=", True),
            ("address_id.state_id", "in", lines.state_ids.ids),
        ]
    )
    locations_by_state = {}
    for work_location in work_locations:
        locations_by_state.setdefault(work_location.address_id.state_id.id, set()).add(
            work_location.resource_calendar_location_id.id
        )
    # One write per distinct location set: sister lines share their states
    # (every Bavarian holiday names Bavaria), and each write runs a -- then
    # idempotent -- synchronisation.
    lines_by_locations = {}
    for line in lines:
        location_ids = tuple(
            sorted(
                {
                    location_id
                    for state in line.state_ids
                    for location_id in locations_by_state.get(state.id, ())
                }
            )
        )
        if location_ids:
            lines_by_locations.setdefault(location_ids, []).append(line.id)
    for location_ids, line_ids in lines_by_locations.items():
        lines.browse(line_ids).write(
            {"location_ids": [Command.link(lid) for lid in location_ids]}
        )
    seeded = sum(len(line_ids) for line_ids in lines_by_locations.values())
    _logger.info(
        "hr_holidays_public_resource: assigned locations to %s of %s "
        "state-scoped public holiday line(s)",
        seeded,
        len(lines),
    )
    return seeded


def post_init_hook(env):
    create_locations_from_work_locations(env)
    seed_line_locations_from_states(env)
