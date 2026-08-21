# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import ValidationError

from .common import TestHolidaysPublicResourceCommon


class TestLocations(TestHolidaysPublicResourceCommon):
    """Public holidays assigned to locations directly.

    Some public holidays are observed only in some municipalities, which no
    state can express -- Augsburg's Friedensfest, say. A line names the
    locations it applies to and reaches the union of that and its states.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location_augsburg = cls._create_location("Augsburg")
        cls.employee_augsburg = cls._create_employee("Emp Augsburg", cls.calendar_by)
        # The employee follows the public holiday location of the work
        # location; there is nothing to assign on the employee directly.
        cls.employee_augsburg.work_location_id.resource_calendar_location_id = (
            cls.location_augsburg
        )

    def _resource_mirror(self, line, employee):
        return self.leave_model.search(
            [
                ("public_holiday_line_id", "=", line.id),
                ("resource_id", "=", employee.resource_id.id),
            ]
        )

    def test_location_line_reaches_only_its_employees(self):
        line = self._create_line(
            self._work_monday(),
            name="Friedensfest",
            locations=self.location_augsburg,
        )
        self.assertTrue(self._resource_mirror(line, self.employee_augsburg))
        self.assertFalse(self._resource_mirror(line, self.employee))
        self.assertFalse(self._resource_mirror(line, self.employee_by))
        # A scoped line never lands on a whole schedule.
        self.assertFalse(
            self.leave_model.search(
                [
                    ("public_holiday_line_id", "=", line.id),
                    ("resource_id", "=", False),
                ]
            )
        )

    def test_states_and_locations_are_a_union(self):
        line = self._create_line(
            self._work_monday(),
            name="Fronleichnam",
            states=self.state_by,
            locations=self.location_augsburg,
        )
        self.assertTrue(self._resource_mirror(line, self.employee_augsburg))
        self.assertTrue(self._resource_mirror(line, self.employee_by))
        self.assertFalse(self._resource_mirror(line, self.employee))

    def test_nationwide_same_day_wins_over_location(self):
        day = self._work_monday()
        location_line = self._create_line(
            day, name="Friedensfest", locations=self.location_augsburg
        )
        national = self._create_line(day, name="National")
        self.assertFalse(self._resource_mirror(location_line, self.employee_augsburg))
        self.assertTrue(
            self.leave_model.search(
                [
                    ("public_holiday_line_id", "=", national.id),
                    ("calendar_id", "=", False),
                    ("company_id", "=", self.company.id),
                ]
            )
        )

    def test_moving_the_employee_moves_the_mirror(self):
        line = self._create_line(
            self._work_monday(),
            name="Friedensfest",
            locations=self.location_augsburg,
        )
        elsewhere_office = self._create_work_location("Elsewhere office", None)
        elsewhere_office.resource_calendar_location_id = self._create_location(
            "Elsewhere"
        )
        augsburg_office = self.employee_augsburg.work_location_id
        self.employee_augsburg.work_location_id = elsewhere_office
        self.assertFalse(self._resource_mirror(line, self.employee_augsburg))
        self.employee_augsburg.work_location_id = augsburg_office
        self.assertTrue(self._resource_mirror(line, self.employee_augsburg))

    def test_assignment_from_the_location_side_resyncs(self):
        nowhere = self._create_location("Nowhere")
        line = self._create_line(
            self._work_monday(), name="Friedensfest", locations=nowhere
        )
        self.assertFalse(self._resource_mirror(line, self.employee_augsburg))
        self.location_augsburg.public_holiday_line_ids = [Command.link(line.id)]
        self.assertTrue(self._resource_mirror(line, self.employee_augsburg))
        self.location_augsburg.public_holiday_line_ids = [Command.unlink(line.id)]
        self.assertFalse(self._resource_mirror(line, self.employee_augsburg))

    def test_location_line_is_no_nationwide_duplicate(self):
        day = self._work_monday()
        self._create_line(day, name="National")
        # Must not raise: the scoped line is not a duplicate of the
        # nationwide one on the same date.
        self._create_line(day, name="Friedensfest", locations=self.location_augsburg)

    def test_duplicate_location_on_one_date_raises(self):
        day = self._work_monday()
        self._create_line(day, name="Friedensfest", locations=self.location_augsburg)
        with self.assertRaises(ValidationError):
            self._create_line(day, name="Doubled", locations=self.location_augsburg)

    def test_clearing_the_locations_makes_the_duplicate_visible(self):
        day = self._work_monday()
        self._create_line(day, name="National")
        scoped = self._create_line(
            day, name="Friedensfest", locations=self.location_augsburg
        )
        with self.assertRaises(ValidationError):
            scoped.location_ids = [Command.clear()]

    def test_a_line_that_lost_its_locations_can_be_disabled(self):
        """The escape hatch for a special day whose locations are gone.

        A line scoped only to locations falls back to applying to everybody
        once those locations are deleted -- nothing is left to scope it.
        Disabling the line takes it out of the synchronisation entirely.
        """
        day = self._work_monday()
        line = self._create_line(
            day, name="Friedensfest", locations=self.location_augsburg
        )
        # Deleting the location clears the link on the work location, and
        # everybody working there follows.
        self.location_augsburg.unlink()
        line._sync_global_leaves()
        # Without a scope the line is nationwide and reaches every company.
        self.assertTrue(
            self.leave_model.search(
                [
                    ("public_holiday_line_id", "=", line.id),
                    ("calendar_id", "=", False),
                    ("company_id", "=", self.company.id),
                ]
            )
        )
        line.active = False
        self.assertFalse(
            self.leave_model.search([("public_holiday_line_id", "=", line.id)])
        )

    def test_next_year_wizard_carries_the_locations(self):
        line = self._create_line(
            self._work_monday(),
            name="Friedensfest",
            locations=self.location_augsburg,
        )
        self.env["calendar.public.holiday.next.year"].create(
            {"public_holiday_ids": [Command.set(self.holiday.ids)]}
        ).create_public_holidays()
        copy = self.line_model.search(
            [
                ("name", "=", "Friedensfest"),
                ("public_holiday_id.year", "=", self.year + 1),
            ]
        )
        self.assertEqual(len(copy), 1)
        self.assertEqual(copy.location_ids, line.location_ids)
