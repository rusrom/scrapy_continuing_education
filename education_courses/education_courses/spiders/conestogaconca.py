# -*- coding: utf-8 -*-
import scrapy
import re
import glob
import csv
import os.path

from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst
from education_courses.items import ConestogacCourseItem

from w3lib.html import replace_escape_chars, replace_entities
from datetime import datetime


def remove_garbage(val):
    val = replace_escape_chars(val)
    val = replace_entities(val)
    val = re.sub(r'\s{2,}', ' ', val)
    return val.strip()


class ConestogaconcaSpider(scrapy.Spider):
    name = 'conestogaconca'
    allowed_domains = ['conestogac.on.ca']
    start_urls = ['https://continuing-education.conestogac.on.ca/courses']

    def parse(self, response):
        courses = response.xpath('//li[@class="mb-1"]/a')
        for course in courses:
            yield response.follow(course, callback=self.parse_course)

    def parse_course(self, response):
        l = ItemLoader(item=ConestogacCourseItem(), response=response)
        l.default_output_processor = TakeFirst()

        course_data = response.xpath('//div[@data-accordion][1]')

        l.add_value('institution_name', 'Conestoga College')
        l.add_xpath('course_code', '//div[@class="hero-banner"]//span/text()')
        l.add_xpath('course_name', '//h1[contains(@class, "text-white")]/text()')
        l.add_value('delivery_types', course_data.xpath('.//small[strong[contains(text(), "Delivery:")]]/following-sibling::small/text()').get())
        l.add_value('url', response.url)
        # l.add_value('faculty', '???????????')
        l.add_xpath('description', '//h2[contains(text(), "Course description")]/following-sibling::p[1]/text()')

        price = course_data.xpath('.//small[strong[contains(text(), "Cost:")]]/following-sibling::small/text()').get()
        if price:
            price = price.lstrip('$')
        else:
            price = '0.0'
        l.add_value('price', [price])

        weekday_time_data = course_data.xpath('.//small[strong[contains(text(), "Day/Time:")]]/following-sibling::small/text()').getall()
        if not weekday_time_data:
            return False
        weekday_time_data = [remove_garbage(data) for data in weekday_time_data]
        # ['Thurs. 9:00am – 4:00pm', 'Fri. 9:00am – 4:00pm']
        weekday_time_data = [data for data in weekday_time_data if len(data) > 1]

        if weekday_time_data:
            weekdays = [re.search(r'(^\w+)', d).group(1) if re.search(r'(^\w+)', d) else '' for d in weekday_time_data]
            weekdays = [d for d in weekdays if d]
        else:
            weekdays = []

        l.add_value('days', [weekdays])
        l.add_value('prerequisite', response.xpath('//strong[contains(text(), "Prerequisites:")]/following-sibling::a/text()').getall())
        l.add_value('corequisites', response.xpath('//strong[contains(text(), "Corequisites:")]/following-sibling::a/text()').getall())
        l.add_value('program', 'Continuing Education')

        if weekday_time_data:
            duration_hours_list = [re.findall(r'\d{1,2}:\d{1,2}\w{2}', t) for t in weekday_time_data]
        else:
            duration_hours_list = []
        l.add_value('duration_hours', duration_hours_list)
        l.add_value('duration_days_week', l.get_collected_values('days'))

        start_date = course_data.xpath('.//small[strong[contains(text(), "Start Date:")]]/following-sibling::small/text()').get()
        if start_date:
            start_date = re.sub(r'(\s*\.\s+|\s*,\s+)', '-', start_date)
            start_date = datetime.strptime(start_date, '%b-%d-%Y')

        end_date = course_data.xpath('.//small[strong[contains(text(), "End date:")]]/following-sibling::small/text()').get()
        if start_date:
            end_date = re.sub(r'(\s*\.\s+|\s*,\s+)', '-', end_date)
            end_date = datetime.strptime(end_date, '%b-%d-%Y')

        duration_month_list = [[start_date, end_date]]

        l.add_value('duration_months', duration_month_list)
        l.add_value('duration_as_string', [
            l.get_collected_values('duration_hours'),
            l.get_collected_values('duration_days_week'),
            l.get_collected_values('duration_months'),
        ])

        hours_site = course_data.xpath('.//small[strong[contains(text(), "Hours:")]]/following-sibling::small/text()').get()
        if not hours_site:
            hours_site = 0

        l.add_value('total_hours', [
            l.get_collected_values('duration_hours'),
            l.get_collected_values('duration_days_week'),
            hours_site,
        ])

        yield l.load_item()

    def close(self, reason):
        current_file = max(glob.iglob('*.csv'), key=os.path.getctime)

        with open(current_file, encoding='utf-8') as f:
            reader = csv.reader(f)
            good_lines = [line for line in reader if line]

        with open(current_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for line in good_lines:
                writer.writerow(line)
