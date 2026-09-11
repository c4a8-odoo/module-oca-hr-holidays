This module depends on `hr_holidays_public`, which carries the public holiday
regions of the employees, and on `calendar_public_holiday_resource`, which
generates the time off. Installing it installs both.

The *Exclude Public Holidays* flag of `hr_holidays_public` has no effect once
this module is installed: every public holiday exists as global time off, and
the standard *Ignore Public Holidays* setting of the leave type decides whether
a leave counts them.
