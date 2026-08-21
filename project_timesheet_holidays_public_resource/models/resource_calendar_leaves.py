# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        leaves._generate_public_holiday_resource_timesheets()
        return leaves

    @api.model
    def _prune_off_contract_public_holiday_timesheets(self, lines):
        """Drop generated public holiday entries on days no contract covers.

        A public holiday only concerns somebody employed on that day. Only
        entries stemming from a generated public holiday are judged --
        hand-made global time off keeps its standard behaviour.
        """
        off_contract = lines.filtered(
            lambda line: line.employee_id
            and line.global_leave_id.public_holiday_line_id
            and not line.employee_id.sudo()._is_in_contract(line.date)
        )
        if off_contract:
            off_contract.write({"global_leave_id": False})
            off_contract.unlink()
        return lines - off_contract

    def _timesheet_create_lines(self):
        # Company-wide public holidays skip the days outside a contract.
        return self._prune_off_contract_public_holiday_timesheets(
            super()._timesheet_create_lines()
        )

    def _generate_public_time_off_timesheets(self, employees):
        # An archived employee can never receive a timesheet -- standard
        # raises instead of skipping, so they are left out up front.
        lines = super()._generate_public_time_off_timesheets(
            employees.filtered("active")
        )
        return self._prune_off_contract_public_holiday_timesheets(lines)

    def _generate_public_holiday_resource_timesheets(self):
        """Timesheet the public holidays that belong to one person.

        ``project_timesheet_holidays`` only timesheets company-wide time off --
        ``_generate_timesheeets`` keeps ``not resource_id`` -- so a regional
        public holiday, which is generated for a single resource, produced
        nothing. The same values are used, so the entries are indistinguishable
        from the nationwide ones.
        """
        candidates = self.filtered(
            lambda leave: leave.resource_id
            and leave.public_holiday_line_id
            and leave.company_id.internal_project_id
            and leave.company_id.leave_timesheet_task_id
        )
        if not candidates:
            return self.env["account.analytic.line"]
        employees = (
            self.env["hr.employee"]
            .sudo()
            .search([("resource_id", "in", candidates.resource_id.ids)])
        )
        employee_by_resource = {
            employee.resource_id.id: employee
            for employee in employees
            if employee.active
        }
        vals_list = []
        for leave in candidates:
            employee = employee_by_resource.get(leave.resource_id.id)
            if not employee:
                continue
            for index, (day, hours) in enumerate(
                leave._public_holiday_resource_work_time(employee)
            ):
                if leave._public_holiday_day_already_accounted(employee, day):
                    continue
                vals_list.append(
                    leave._timesheet_prepare_line_values(
                        index, employee, [(day, hours)], day, hours
                    )
                )
        return self.env["account.analytic.line"].sudo().create(vals_list)

    def _public_holiday_resource_work_time(self, employee):
        """Hours the employee would have worked on this public holiday."""
        self.ensure_one()
        calendar = self.calendar_id or employee.resource_calendar_id
        if not calendar:
            return []
        # Without ignoring itself the day is already free and yields nothing.
        return employee.sudo()._list_work_time_per_day(
            self.date_from,
            self.date_to,
            calendar=calendar,
            domain=[("id", "not in", self.ids)],
        )[employee.id]

    def _public_holiday_day_already_accounted(self, employee, day):
        """Whether that day is covered by a leave or a timesheet already."""
        self.ensure_one()
        leave_model = self.env["hr.leave"].sudo()
        if leave_model.search_count(
            [
                ("employee_id", "=", employee.id),
                ("state", "=", "validate"),
                ("date_from", "<=", f"{day} 23:59:59"),
                ("date_to", ">=", f"{day} 00:00:00"),
            ],
            limit=1,
        ):
            return True
        return bool(
            self.env["account.analytic.line"]
            .sudo()
            .search_count(
                [
                    ("employee_id", "=", employee.id),
                    ("date", "=", day),
                    ("global_leave_id", "!=", False),
                ],
                limit=1,
            )
        )
