# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command

from .common import TestHolidaysPublicResourceCommon


class TestLocationOverview(TestHolidaysPublicResourceCommon):
    """The read-only overview on the public holiday location form.

    A union of everything somebody assigned to the location gets: the
    nationwide public holidays and the ones assigned to it directly.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls._create_location("Augsburg", company=cls.company)
        cls.location_plain = cls._create_location("Elsewhere", company=cls.company)
        day = cls._work_monday()
        cls.line_national = cls._create_line(day, name="National")
        cls.line_direct = cls._create_line(
            day + timedelta(days=1), name="Friedensfest", locations=cls.location
        )

    def _overview(self, location):
        location.invalidate_recordset(["public_holiday_overview_line_ids"])
        return location.public_holiday_overview_line_ids

    def test_nationwide_shows_everywhere(self):
        self.assertIn(self.line_national, self._overview(self.location))
        self.assertIn(self.line_national, self._overview(self.location_plain))

    def test_direct_assignment_shows_only_there(self):
        self.assertIn(self.line_direct, self._overview(self.location))
        self.assertNotIn(self.line_direct, self._overview(self.location_plain))

    def test_assignment_change_updates_the_overview(self):
        self.line_direct.location_ids = [Command.link(self.location_plain.id)]
        self.assertIn(self.line_direct, self._overview(self.location_plain))

    def test_foreign_country_is_ruled_out(self):
        foreign = self.line_model.create(
            {
                "name": "Foreign national",
                "date": self._work_monday() + timedelta(days=2),
                "public_holiday_id": self.holiday_model.create(
                    {"year": self.year, "country_id": self.env.ref("base.fr").id}
                ).id,
            }
        )
        self.assertNotIn(foreign, self._overview(self.location))

    def test_a_location_without_a_company_sees_everything(self):
        """An unknown company country cannot rule a holiday calendar out."""
        shared = self._create_location("Shared")
        self.assertIn(self.line_national, self._overview(shared))

    def test_overview_is_readonly(self):
        field = self.env["resource.calendar.location"]._fields[
            "public_holiday_overview_line_ids"
        ]
        self.assertTrue(field.compute)
        self.assertTrue(field.readonly)
        self.assertFalse(field.store)
