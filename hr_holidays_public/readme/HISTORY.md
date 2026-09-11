## 19.0.2.0.0

- The *Exclude Public Holidays* flag of the leave type is replaced by the
  standard *Ignore Public Holidays* setting, which means the opposite.
  Upgrading carries the value over.
- Public holidays follow the public holiday region of the employee, derived
  from their work location, instead of the state of their work address.
  Upgrading links every work location to the region created from its state
  by `calendar_public_holiday`, or gives it a region of its own, owned by
  its company. The country of the region selects the public holiday
  calendars.
