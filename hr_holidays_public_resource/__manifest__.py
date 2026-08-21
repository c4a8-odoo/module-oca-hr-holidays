# Copyright 2026 glueckkanja AG
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "HR Holidays Public on Working Schedules",
    "summary": "Use the standard Odoo time off machinery for public holidays "
    "configured through the public holiday calendar",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "Human Resources",
    "author": "glueckkanja AG, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-holidays",
    "depends": ["calendar_public_holiday_resource", "hr_holidays"],
    # hr_holidays_public implements the very same feature through a private
    # `_attendance_intervals_batch` override no standard module knows about.
    # Running both would apply two competing engines at once.
    "excludes": ["hr_holidays_public"],
    "demo": [
        "demo/hr_holidays_public_resource_demo.xml",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/resource_calendar_leaves_views.xml",
        "views/calendar_public_holiday_view.xml",
        "views/resource_calendar_location_views.xml",
        "views/hr_work_location_views.xml",
        "views/hr_employee_views.xml",
        "views/resource_calendar_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_holidays_public_resource/static/src/**/*.js",
            "hr_holidays_public_resource/static/src/**/*.xml",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
}
