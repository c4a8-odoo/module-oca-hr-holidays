This module replaces `hr_holidays_public` and declares it as incompatible, so
the two can never be installed at the same time.

Recommended order:

1. uninstall `hr_holidays_public`;
2. install `calendar_public_holiday_resource`, which generates the time off of
   the current year onwards and logs any public holiday it could not apply;
3. install this module.
