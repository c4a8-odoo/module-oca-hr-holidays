Whether a leave counts a public holiday is the standard *Ignore Public
Holidays* setting on the leave type.

**Nationwide public holidays** are generated once per company, as a global
time off without working hours that reaches every working schedule of the
company, and they appear in the standard Public Holidays list. A public
holiday line can also name **additional working schedules**, which get an
entry carrying the schedule wherever no company-wide record already applies
-- a special day for one shift plan, say.

**Regional public holidays** follow the region of the **work location** of
each employee -- where the work is actually done -- and are generated for that
person alone. The work address of an employee record is usually the company
address and says nothing about the region, so an employee without a work
location only gets the nationwide ones. They are therefore not in the
Public Holidays list, which is company-wide: they show on the person's own time
off calendar, count against their leaves, appear in the gantt and produce their
timesheet entry. Colleagues sharing one working schedule but working in
different states each get their own.

A region does not have to be a whole state. Every employee carries a
**public holiday location** (*resource.calendar.location*, shown read-only
on the Payroll tab, below the working hours) -- a plain label of where they
work, without the address a standard work location demands. It is derived
from the work location of each version (contract): the mapping is
maintained once, on the work location. A public holiday line can name
locations directly, next to (or instead of) its states: everybody assigned
to one of the line's locations *or* whose work location is in one of its
states gets the day. This covers public holidays observed only in some
municipalities -- Augsburg's Friedensfest, or Assumption Day in the Catholic
municipalities of Bavaria -- where assigning people the right location is
far easier than expressing the geography per holiday. The assignment is
maintained on the public holiday line; while editing, an empty location cell
reads *All Locations*. The *Create Next Year* copy carries the locations of
each line over to the new year. Installing the module bootstraps the
locations from the existing work locations -- one per distinct work address,
linked back to its work locations -- and everybody follows through their
work location automatically. Every line with *Related
States* is then seeded with the locations whose origin work address lies in
one of them; the states are kept, so the seeding changes nothing about who
gets which day until somebody edits the lines.

A line whose locations are all gone loses its scope and would fall back
to applying to everybody. Disable the line instead of deleting it: it then
generates no time off but keeps its configuration for the day the locations
return. Whether the employees of a schedule get the personal entries of
regional public holidays at all is the *Apply Employee Public Holidays*
setting of the working schedule.

The public holiday location form shows a read-only overview of every public
holiday applying there: the nationwide ones and the ones assigned to it
directly. The working schedule form shows the same kind of overview for the
days that reach the schedule: the nationwide ones of its companies, plus the
regional and location-scoped days resolved from its employees.

The work location and the working schedule of an employee live on their
versions (contracts), and the public holidays follow the version valid on
their day: a contract change in October moves the October holidays to the
new location and schedule without touching the March ones, including for
versions dated in the future. A day no contract covers is given to nobody --
an employee without a contract gets no public holidays at all.

A calendar shown for nobody in particular only shows the nationwide public
holidays as free days, since a regional one belongs to a person.

The public holiday template shows how far it reaches, with a smart button for
the working schedules its nationwide holidays are put on and one for all the
employees it gives a day off.
