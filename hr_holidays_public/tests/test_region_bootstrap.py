# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.hr_holidays_public.hooks import create_regions_from_work_locations


class TestRegionBootstrapCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.country = cls.env["res.country"].create(
            {"name": "Bootstrap Country", "code": "XB"}
        )
        cls.region_model = cls.env["calendar.public.holiday.region"]

    @classmethod
    def _create_work_location(cls, name, state=None, company=None):
        address = cls.env["res.partner"].create(
            {
                "name": f"{name} address",
                "country_id": cls.country.id,
                "state_id": state.id if state else False,
            }
        )
        return cls.env["hr.work.location"].create(
            {
                "name": name,
                "company_id": (company or cls.company).id,
                "address_id": address.id,
            }
        )

    @classmethod
    def _create_employee(cls, name, work_location):
        return cls.env["hr.employee"].create(
            {
                "name": name,
                "company_id": cls.company.id,
                "work_location_id": work_location.id if work_location else False,
            }
        )


class TestRegionBootstrap(TestRegionBootstrapCommon):
    """Installing the module builds the regions from the work locations.

    One public holiday region per distinct work address, linked back to the
    work locations it stands for, with everybody assigned through the work
    location of their versions.
    """

    def test_one_region_per_distinct_address(self):
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
        third = self._create_work_location("Elsewhere")
        create_regions_from_work_locations(self.env)
        self.assertTrue(first.public_holiday_region_id)
        self.assertEqual(
            first.public_holiday_region_id,
            second.public_holiday_region_id,
            "one address, one region",
        )
        self.assertNotEqual(
            first.public_holiday_region_id, third.public_holiday_region_id
        )
        self.assertEqual(
            first.public_holiday_region_id.name,
            "Back office",
            "the region is named after the work location -- the first by "
            "the model's name ordering when several share the address",
        )
        self.assertEqual(first.public_holiday_region_id.company_id, self.company)

    def test_employees_are_assigned_through_their_work_location(self):
        office = self._create_work_location("Office")
        employee = self._create_employee("Emp Office", office)
        create_regions_from_work_locations(self.env)
        self.assertTrue(employee.public_holiday_region_id)
        self.assertEqual(
            employee.public_holiday_region_id, office.public_holiday_region_id
        )

    def test_the_assignment_follows_a_relinked_work_location(self):
        office = self._create_work_location("Office")
        employee = self._create_employee("Emp Office", office)
        create_regions_from_work_locations(self.env)
        moved = self.region_model.create({"name": "Moved"})
        office.public_holiday_region_id = moved
        self.assertEqual(
            employee.public_holiday_region_id,
            moved,
            "the employee follows the work location's public holiday region",
        )

    def test_the_bootstrap_is_idempotent(self):
        self._create_work_location("Office")
        created = create_regions_from_work_locations(self.env)
        self.assertTrue(created)
        self.assertFalse(
            create_regions_from_work_locations(self.env),
            "a second run finds every work location already linked",
        )

    def test_an_employee_without_a_work_location_stays_unassigned(self):
        loner = self._create_employee("Emp Loner", None)
        create_regions_from_work_locations(self.env)
        self.assertFalse(loner.public_holiday_region_id)


class TestStateRegionLink(TestRegionBootstrapCommon):
    """A work location in a former public holiday state follows that state.

    ``calendar_public_holiday`` turns the states its lines used to be scoped
    to into shared regions named after the state. A work location whose
    address lies in such a state is linked to that region rather than given
    one of its own, so that the people working there keep the public
    holidays of their region.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Names no real database carries, so the lookup by name is exact.
        cls.state_by = cls.env["res.country.state"].create(
            {"name": "Bootstrap Bayern", "code": "TBY", "country_id": cls.country.id}
        )
        cls.state_nw = cls.env["res.country.state"].create(
            {"name": "Bootstrap Nordrhein", "code": "TNW", "country_id": cls.country.id}
        )
        cls.state_region = cls.region_model.create({"name": "Bootstrap Bayern"})

    def test_a_work_location_in_the_state_is_linked_to_its_region(self):
        office = self._create_work_location("Munich office", self.state_by)
        created = create_regions_from_work_locations(self.env)
        self.assertEqual(office.public_holiday_region_id, self.state_region)
        self.assertNotIn(self.state_region, created, "reused, not created")

    def test_a_disambiguated_state_name_is_found_too(self):
        twin = self.region_model.create(
            {"name": f"Bootstrap Nordrhein ({self.country.code})"}
        )
        office = self._create_work_location("Cologne office", self.state_nw)
        create_regions_from_work_locations(self.env)
        self.assertEqual(office.public_holiday_region_id, twin)

    def test_a_state_without_a_region_gets_one_per_address(self):
        self.state_region.unlink()
        office = self._create_work_location("Munich office", self.state_by)
        created = create_regions_from_work_locations(self.env)
        self.assertIn(office.public_holiday_region_id, created)
        self.assertEqual(office.public_holiday_region_id.name, "Munich office")


@tagged("post_install", "-at_install")
class TestStateRegionLinkCompany(TestStateRegionLink):
    """Run once everything is loaded: creating a company needs the defaults
    other modules add to ``res.company``."""

    def test_a_region_of_another_company_is_not_taken(self):
        other = self.env["res.company"].create({"name": "Other Co"})
        self.state_region.company_id = other
        office = self._create_work_location("Munich office", self.state_by)
        create_regions_from_work_locations(self.env)
        self.assertNotEqual(office.public_holiday_region_id, self.state_region)
