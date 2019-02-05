# -*- coding: utf-8 -*-

import scrapy
import re

from scrapy.loader.processors import MapCompose, Identity, Compose
from w3lib.html import replace_escape_chars

from datetime import datetime


def remove_exra_spaces(val):
    return re.sub(r'\s{2,}', ' ', val)


def remove_space_garbage(val):
    val = replace_escape_chars(val)
    return re.sub(r'\s{2,}', ' ', val)


# TODO: Get datime from string and get timedelta
def get_days(val):
    res = re.findall(r'\d+-\w+-\d+', val)
    if len(res) < 2:
        return res[0] + '!!!!'
    else:
        min_date, max_date = res
        return 'min: {} and MAX: {}'.format(min_date, max_date)


def get_duration_hours(val):
    intervals = re.findall(r'(\d+:\d+\w{,2})', val[0])

    if len(intervals) > 2:
        result = []
        # We have more then 1 timeinterval

        # Get by couple time intervals from intervals
        for start_time, end_time in zip(intervals[::2], intervals[1::2]):
            start_time = datetime.strptime(start_time, '%I:%M%p')
            end_time = datetime.strptime(end_time, '%I:%M%p')
            duration_hours = (end_time - start_time).seconds / 3600
            result.append(duration_hours)
        min_duration = min(result)
        max_duration = max(result)
        # return '[{0:.1f}, {1:.1f}]'.format(int(min_duration), int(max_duration))
    else:
        # we have 1 timeinterval
        start_time, end_time = intervals
        start_time = datetime.strptime(start_time, '%I:%M%p')
        end_time = datetime.strptime(end_time, '%I:%M%p')
        duration_hours = (end_time - start_time).seconds / 3600
        # return '[{0:.1f}, {0:.1f}]'.format(int(duration_hours))
        min_duration = duration_hours
        max_duration = duration_hours

    val[0] = [min_duration, max_duration]
    return val


def get_duration_month(val):
    dates = re.findall(r'\d+-\w+-\d+', val[0])
    start_date, end_date = dates
    start_date = datetime.strptime(start_date, '%d-%b-%Y')
    end_date = datetime.strptime(end_date, '%d-%b-%Y')
    duration_days = round((end_date - start_date).days / 30)
    val[0] = [duration_days, duration_days]
    return val


# Get weekdays: Thursday,Sunday
def get_week_days(val):
    return re.findall(r'([A-Za-z]+)\s*\d+:\d+\w{,2}', val)


# Get duration days of week: [2.0, 2.0]
def get_duration_weekdays(val):
    weekday_count = re.findall(r'([A-Za-z]+)\s*\d+:\d+\w{,2}', val[0])
    count = len(weekday_count)
    val[0] = [count, count]
    return val
    # return '[{0:.1f}, {0:.1f}]'.format(len(weekday_count))


def calculate_total_hours(val):
    # print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!{}->>>>{}'.format(type(val), val))
    res = list(map(lambda hours_week, days_week: hours_week * days_week, val[0], val[1]))
    return res


# def formating_duration_string(val):
#     print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!{}->>>>{}'.format(type(val), val))
#     return val


class EducationCoursesItem(scrapy.Item):

    institution_name = scrapy.Field()
    course_code = scrapy.Field(
        input_processor=MapCompose(
            lambda x: x.strip(),
            lambda x: x.split()[0],
        )
    )
    course_name = scrapy.Field(
        input_processor=MapCompose(
            lambda x: x.strip(),
            lambda x: ' '.join(x.split()[1:]),
        )
    )
    delivery_types = scrapy.Field(
        input_processor=MapCompose(
            remove_space_garbage,
            lambda x: re.findall(r'(Onsite|Offsite)', x),
            lambda x: x.replace('Onsite', 'In Class').replace('Offsite', 'Online')
        ),
        # output_processor=Identity(),
    )
    url = scrapy.Field()
    faculty = scrapy.Field()
    description = scrapy.Field()
    location = scrapy.Field()
    subject = scrapy.Field()

    # price = scrapy.Field()
    price = scrapy.Field(
        input_processor=Compose(
            lambda x: '[{0}, {0}]'.format(x[0][:-1]),
        )
    )

    duration_as_string = scrapy.Field(
        # input_processor=Compose(
        #     formating_duration_string,
        # ),
        output_processor=Compose(
            lambda x: '{0} hrs/day, {1} days/week for {2} months'.format(x[0], x[1], x[2])
        )
    )
    days = scrapy.Field(
        input_processor=MapCompose(
            remove_space_garbage,
            # lambda x: re.findall(r'([A-Za-z]+)\s*\d+:\d+\w{,2}', x)
            get_week_days,
        ),
        output_processor=Identity(),
    )
    prerequisite = scrapy.Field()
    capacity = scrapy.Field()
    corequisites = scrapy.Field()
    program = scrapy.Field()
    duration_hours = scrapy.Field(
        input_processor=Compose(
            # remove_space_garbage,
            get_duration_hours,
        ),
        output_processor=Compose(
            lambda x: '[{0}, {1}]'.format(x[0][0], x[0][1])
        )
    )
    duration_days_week = scrapy.Field(
        input_processor=Compose(
            lambda x: [remove_space_garbage(val) for val in x],
            get_duration_weekdays,
        ),
        output_processor=Compose(
            # lambda x: '[{0:.1f}, {0:.1f}]'.format(len(x[0]) if x[0] else 0)
            lambda x: '[{0:.1f}, {1:.1f}]'.format(x[0][0], x[0][1])
        ),

    )
    duration_months = scrapy.Field(
        input_processor=Compose(
            get_duration_month,
        ),
        output_processor=Compose(
            lambda x: '[{0:.1f}, {1:.1f}]'.format(x[0][0], x[0][1])
        )
    )

    total_hours = scrapy.Field(
        # input_processor=MapCompose(
        #     lambda x: x.replace('.00', '')
        # )
        input_processor=Compose(
            calculate_total_hours,
        ),
        output_processor=Compose(
            lambda x: '[{0}, {1}]'.format(x[0], x[1])
        )
    )
