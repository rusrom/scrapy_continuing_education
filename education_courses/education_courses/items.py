# -*- coding: utf-8 -*-

import scrapy
import re

from scrapy.loader.processors import MapCompose, Identity, Compose
from w3lib.html import replace_escape_chars, replace_entities

from datetime import datetime


def remove_exra_spaces(val):
    return re.sub(r'\s{2,}', ' ', val)


def remove_garbage(val):
    val = replace_escape_chars(val)
    val = replace_entities(val)
    val = re.sub(r'\s{2,}', ' ', val)
    return val.strip()


def get_prices(val):
    if len(val) > 1:
        # More then 1 orice
        prices = []
        for price in val:
            price = price.replace(',', '')
            try:
                price = round(float(price), 2)
            except ValueError:
                continue
            prices.append(price)
        if prices:
            price_min = min(prices)
            price_max = max(prices)
        else:
            price_min = 0.0
            price_max = 0.0
    else:
        # Only 1 price
        # Remove comma as thousand separator
        price = val[0].replace(',', '')
        try:
            price = round(float(price), 2)
            price_min = price
            price_max = price
        except ValueError:
            price_min = 0.0
            price_max = 0.0

    val = [price_min, price_max]
    return val


def get_days(val):
    # clear val list from empty [] list
    if val:
        days_intervals = [days for days in val if days and days[0].strip()]
        if days_intervals:
            res = []
            for i in days_intervals:
                res += i
            val = list(set(res))
        else:
            val = []

    return val


# Get min amd max timedelta from list of strings ['9:00', '15:30', '9:00', '13:00'] or ['9:00', '15:30']
def get_timeinterval(val):
    result = []
    # Correct 24 hours to 00 hours
    val = [i.replace('24', '00') for i in val]
    # Iterate through all pairs of time start -time end
    for start_time, end_time in zip(val[::2], val[1::2]):
        start_time = datetime.strptime(start_time, '%H:%M')
        end_time = datetime.strptime(end_time, '%H:%M')
        # Calculate duration between start time and end time
        duration_hours = (end_time - start_time).seconds / 3600
        result.append(duration_hours)
    return result


def get_duration_hours(val):
    # Get all not empty [] lists with intervals
    time_intervals = [interval for interval in val if interval]
    amount_of_time_intervals = len(time_intervals)
    if amount_of_time_intervals > 1:
        # Several timeintervals like this [['18:00', '22:30'], ['9:30', '17:30'], ['13:00', '17:00']]
        result = []
        for list_with_times in time_intervals:
            durations = get_timeinterval(list_with_times)
            # Add list of durations to result list with all durations
            result += durations
        min_duration = min(result)
        max_duration = max(result)
    elif amount_of_time_intervals == 1:
        # 1 timeinterval [['17:45', '21:05']]
        durations = get_timeinterval(time_intervals[0])
        min_duration = min(durations)
        max_duration = max(durations)
    else:
        # No timeinterval []
        min_duration = 0.0
        max_duration = 0.0

    val = [round(min_duration, 1), round(max_duration, 1)]
    return val


def get_duration_days_week(val):
    if val:
        result = []
        for days in val:
            days_amount = len(days.split(', '))
            result.append(days_amount)
        min_days = float(min(result))
        max_days = float(max(result))
    else:
        min_days = 0.0
        max_days = 0.0
    val = [min_days, max_days]
    return val


def get_total_hours(val):
    hours, days, hours_site = val
    if sum(hours):
        val = list(map(lambda x, y: x * y, hours, days))
    else:
        try:
            hours_site = float(hours_site)
        except ValueError:
            hours_site = 0.0
        val = [hours_site, hours_site]
    return val


def get_month(vals):
    year = '2019'
    mon_abbr = {
        'Jan': 'January',
        'Feb': 'February',
        'Mar': 'March',
        'Apr': 'April',
        'May': 'May',
        'Jun': 'June',
        'Jul': 'July',
        'Aug': 'August',
        'Sep': 'September',
        'Oct': 'October',
        'Nov': 'November',
        'Dec': 'December',
    }

    gazer = []
    for val in vals:
        val = re.sub(r',*\s*{}\s*$'.format(year), '', val)
        val = re.sub(r'\s{2,}', ' ', val)
        val = val.replace('.', '')
        val = val.strip()
        if '–' in val:
            val = val.split('–')
            val = list(map(lambda x: x.strip(), val))

            mons = ''
            result = []
            for d in val:
                mon, dat = re.search(r'([A-Za-z]*)\s*(\d+)', d).groups()
                if mon:
                    mons = mon
                else:
                    mon = mons
                result.append('{}-{}-{}'.format(mon, dat, year))

            cleaned = []
            for str_date in result:
                m, d, y = str_date.split('-')
                if m in mon_abbr.keys():
                    m = mon_abbr[m[:3]]
                cleaned.append('{}-{}-{}'.format(m, d, y))
            gazer.append(cleaned)
        else:
            try:
                m, d = val.split(' ')
                gazer.append(['{}-{}-{}'.format(m, d, year)])
            except ValueError:
                gazer.append([val.replace(' ', '-')])

    return gazer


# Input list of lists of dates intervals [['January-13-2019', 'March-20-2019'], ['March-30-2019', 'June-5-2019']]
def get_duration_months(val):
    if len(val) > 1:
        # delete all lists with only 1 date inside
        data_intervals = [i for i in val if len(i) > 1]
        gazer = []
        for interval in data_intervals:
            start_date, end_date = interval
            start_date = datetime.strptime(start_date, '%B-%d-%Y')
            end_date = datetime.strptime(end_date, '%B-%d-%Y')
            duration_days = round((end_date - start_date).days / 30, 2)
            gazer.append(duration_days)
        min_month_dur = min(gazer)
        max_month_dur = max(gazer)
        val = [min_month_dur, max_month_dur]
    else:
        # 1 date interval
        if len(val[0]) > 1:
            # 2 dates inside date interval
            start_date, end_date = val[0]
            start_date = datetime.strptime(start_date, '%B-%d-%Y')
            end_date = datetime.strptime(end_date, '%B-%d-%Y')
            duration_days = round((end_date - start_date).days / 30, 2)
            val = [duration_days, duration_days]
        else:
            # 1 date inside date intrval
            val = [0.0, 0.0]
    return val


def get_delyvery_type(val):
    if sum(val):
        val = 'Onsite'
    else:
        val = "Blended"
    return val


class ConcordiaCourseItem(scrapy.Item):
    institution_name = scrapy.Field()
    course_code = scrapy.Field(
        input_processor=MapCompose(
            lambda x: x.replace('Course Code: ', ''),
            remove_garbage,
        )
    )
    course_name = scrapy.Field(
        input_processor=MapCompose(
            remove_garbage,
            lambda x: x.lower().title(),
        )
    )
    delivery_types = scrapy.Field(
        input_processor=Compose(
            get_delyvery_type,
        )
    )
    url = scrapy.Field()
    faculty = scrapy.Field()
    description = scrapy.Field(
        input_processor=Compose(
            MapCompose(remove_garbage),
            lambda x: ' '.join(x),
        )
    )
    location = scrapy.Field()
    subject = scrapy.Field()
    price = scrapy.Field(
        input_processor=Compose(
            get_prices,
        ),
        output_processor=Compose(
            lambda x: str(x),
        )
    )
    duration_as_string = scrapy.Field(
        output_processor=Compose(
            lambda x: '{} hrs/day, {} days/week for {} months'.format(*x),
        )
    )
    days = scrapy.Field(
        input_processor=Compose(
            get_days,
            MapCompose(
                lambda x: re.sub(r'\s+', ', ', x),
            )
        ),
        output_processor=Compose(
            lambda x: ' | '.join(x),
        )
    )
    prerequisite = scrapy.Field()
    capacity = scrapy.Field()
    corequisites = scrapy.Field()
    program = scrapy.Field()
    duration_hours = scrapy.Field(
        input_processor=Compose(
            get_duration_hours,
        ),
        output_processor=Compose(
            lambda x: str(x),
        )
    )
    duration_days_week = scrapy.Field(
        input_processor=Compose(
            get_duration_days_week,
        ),
        output_processor=Compose(
            lambda x: str(x),
        )
    )
    duration_months = scrapy.Field(
        input_processor=Compose(
            MapCompose(
                remove_garbage,
            ),
            lambda x: [i for i in x if i],
            get_month,
            get_duration_months,
        ),
        output_processor=Identity()
    )
    total_hours = scrapy.Field(
        input_processor=Compose(
            get_total_hours,
        ),
        output_processor=Identity()
    )


class CamosunCourseItem(scrapy.Item):
    institution_name = scrapy.Field()
    course_code = scrapy.Field()
    course_name = scrapy.Field()
    delivery_types = scrapy.Field()
    url = scrapy.Field()
    faculty = scrapy.Field()
    description = scrapy.Field()
    location = scrapy.Field()
    subject = scrapy.Field()
    price = scrapy.Field(
        # input_processor=Compose(
        #     lambda x: print('>>>>>>>>>>>', x),
        # )
    )
    duration_as_string = scrapy.Field()
    days = scrapy.Field()
    prerequisite = scrapy.Field()
    capacity = scrapy.Field()
    corequisites = scrapy.Field()
    program = scrapy.Field()
    duration_hours = scrapy.Field()
    duration_days_week = scrapy.Field()
    duration_months = scrapy.Field()
    total_hours = scrapy.Field()
