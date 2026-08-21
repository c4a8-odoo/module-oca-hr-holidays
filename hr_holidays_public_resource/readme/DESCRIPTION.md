Makes the standard Odoo time off machinery use the public holidays configured
in the public holiday calendar, instead of a parallel implementation.

`calendar_public_holiday_resource` materialises every public holiday as time
off, which is what standard Odoo keys all of its public holiday behaviour on.
This module adds the HR side of that integration:

- public holidays are excluded from the duration of a leave, controlled by the
  standard *Ignore Public Holidays* setting of the leave type;
- they are greyed out as unusual days in the time off calendar and shown as
  unavailable in gantt views;
- leaves and timesheets that were already approved are recomputed when a public
  holiday is added, moved or removed;
- with `project_timesheet_holidays` installed, a timesheet entry is generated on
  a public holiday for every employee it applies to -- the regional, per-person
  part of this is provided by the `project_timesheet_holidays_public_resource`
  bridge module, which installs automatically;
- regional public holidays are resolved to the employees whose work location is
  in the region, so that colleagues sharing a working schedule keep their own;
- a public holiday line can also be assigned to public holiday locations
  directly -- a lean location model every employee is assigned to -- for
  public holidays observed only in some municipalities, which no state can
  express;
- the public holiday location form shows a read-only overview of every public holiday
  applying there.

This module replaces `hr_holidays_public`, which it excludes: that module solves
the same problem through a private `_attendance_intervals_batch` override that
no standard module is aware of.
