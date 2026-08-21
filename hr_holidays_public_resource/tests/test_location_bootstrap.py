# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.hr_holidays_public_resource.hooks import (
    create_locations_from_work_locations,
    seed_line_locations_from_states,
)

from .common import TestHolidaysPublicResourceCommon


class TestLocationBootstrap(TestHolidaysPublicResourceCommon):
    """Installing the module builds the locations from the work locations.

    One public holiday location per distinct work address, linked back to
    the work locations it stands for, with everybody assigned through the
    work location of their versions.
    """

    def test_one_location_per_distinct_address(self):
        address = self.env["res.partner"].create(
            {"name": "Shared office address", "country_id": self.country.id}
        )
        first = self.env["hr.work.location"].create(
            {
                "name": "Front office",
                "company_id": self.company.id,
                "address_id": address.id,
            }
        )
        second = self.env["hr.work.location"].create(
            {
                "name": "Back office",
                "company_id": self.company.id,
                "address_id": address.id,
            }
        )
        third = self._create_work_location("Elsewhere", None)
        create_locations_from_work_locations(self.env)
        self.assertTrue(first.resource_calendar_location_id)
        self.assertEqual(
            first.resource_calendar_location_id,
            second.resource_calendar_location_id,
            "one address, one location",
        )
        self.assertNotEqual(
            first.resource_calendar_location_id,
            third.resource_calendar_location_id,
        )
        self.assertEqual(
            first.resource_calendar_location_id.name,
            "Back office",
            "the location is named after the work location -- the first by "
            "the model's name ordering when several share the address",
        )
        self.assertEqual(first.resource_calendar_location_id.company_id, self.company)

    def test_employees_are_assigned_through_their_work_location(self):
        create_locations_from_work_locations(self.env)
        self.assertTrue(self.employee.resource_calendar_location_id)
        self.assertEqual(
            self.employee.resource_calendar_location_id,
            self.employee.work_location_id.resource_calendar_location_id,
        )

    def test_the_assignment_follows_a_relinked_work_location(self):
        create_locations_from_work_locations(self.env)
        moved = self._create_location("Moved")
        self.employee.work_location_id.resource_calendar_location_id = moved
        self.assertEqual(
            self.employee.resource_calendar_location_id,
            moved,
            "the employee follows the work location's public holiday location",
        )

    def test_the_bootstrap_is_idempotent(self):
        created = create_locations_from_work_locations(self.env)
        self.assertTrue(created)
        self.assertFalse(
            create_locations_from_work_locations(self.env),
            "a second run finds every work location already linked",
        )

    def test_an_employee_without_a_work_location_stays_unassigned(self):
        loner = self._create_employee("Emp Loner", self.calendar, work_location=False)
        create_locations_from_work_locations(self.env)
        self.assertFalse(loner.resource_calendar_location_id)


class TestLineLocationSeed(TestHolidaysPublicResourceCommon):
    """State-scoped lines are seeded with the locations of their states.

    A location's state is the one of the work address of the work location
    it was built from; every line with *Related States* is given the
    locations whose origin lies in one of them. The states are kept -- the
    two scopes are a union, so the seeding changes nothing about who gets
    which day.
    """

    def _seed(self):
        create_locations_from_work_locations(self.env)
        return seed_line_locations_from_states(self.env)

    def test_state_scoped_lines_get_the_locations_of_their_states(self):
        line_by = self._create_line(
            self._work_monday(), name="Fronleichnam", states=self.state_by
        )
        self._seed()
        location_by = self.employee_by.work_location_id.resource_calendar_location_id
        self.assertIn(location_by, line_by.location_ids)
        self.assertTrue(line_by.state_ids, "the states are kept")
        # A location whose origin has no region stays out.
        location_plain = self.employee.work_location_id.resource_calendar_location_id
        self.assertNotIn(location_plain, line_by.location_ids)

    def test_a_nationwide_line_is_left_alone(self):
        national = self._create_line(self._work_monday(), name="National")
        self._seed()
        self.assertFalse(national.location_ids)

    def test_a_location_of_another_state_stays_out(self):
        nw_office = self._create_work_location("NW office", self.state_nw)
        line_by = self._create_line(
            self._work_monday(), name="Fronleichnam", states=self.state_by
        )
        self._seed()
        self.assertNotIn(nw_office.resource_calendar_location_id, line_by.location_ids)

    def test_an_archived_location_is_not_linked(self):
        gone_office = self._create_work_location("Gone office", self.state_by)
        line_by = self._create_line(
            self._work_monday(), name="Fronleichnam", states=self.state_by
        )
        create_locations_from_work_locations(self.env)
        gone_office.resource_calendar_location_id.active = False
        seed_line_locations_from_states(self.env)
        self.assertNotIn(
            gone_office.resource_calendar_location_id,
            line_by.with_context(active_test=False).location_ids,
        )
