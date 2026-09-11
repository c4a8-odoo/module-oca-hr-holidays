Go to *Time Off -\> Configuration -\> Time Off Types* and open a Leave
Type

- Leave the standard "Ignore Public Holidays" unchecked to exclude public
  holidays from the leave duration; check it to count them.

Go to *Employees -\> Configuration -\> Work Locations* and open a work
location

- Set its *Public Holiday Region*. Everybody whose contract names this work
  location follows it; the region shows read-only on the employee, on the
  Payroll tab below the working hours. Regions are maintained under
  *Time Off -\> Configuration -\> Public Holidays (OCA) -\> Public Holiday
  Regions*.

Installing the module links every work location to a region: the region
named after the state of its address where `calendar_public_holiday` created
one from the former related states, otherwise one region per distinct work
address.
