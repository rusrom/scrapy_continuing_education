# -*- coding: utf-8 -*-
import scrapy
import re
import glob
import csv
import os.path

from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst
from education_courses.items import WcsuwocaCourseItem

from w3lib.html import replace_escape_chars, replace_entities
from datetime import datetime
from scrapy.utils.response import open_in_browser


def remove_garbage(val):
    val = re.sub(r'\s+,\s{2,}', ', ', val)
    val = re.sub(r'\s{2,}', ' ', val)
    val = replace_escape_chars(val)
    val = replace_entities(val)
    return val.strip()


class WcsuwocaSpider(scrapy.Spider):
    name = 'wcsuwoca'
    allowed_domains = ['uwo.ca']
    start_urls = ['https://wcs.uwo.ca/public/listProgramAreas.do?method=load']

    custom_settings = {
        'ITEM_PIPELINES': {
            'education_courses.pipelines.DuplicatesPipeline': 10,
        },
    }

    def parse(self, response):
        programs = response.xpath('//div[@id="programAreasAccordion"]/div[@class="panel panel-default"]')
        for program in programs:
            program_name = program.xpath('./div[contains(@class, "panel-heading")]//span[@class="programArea"]/a/text()').get()

            subjects = program.xpath('./div[contains(@id, "programAreaDetails")]//tr/td[@class="programStream"]')
            for subject in subjects:
                subject_name = subject.xpath('./a/text()').get()
                subject_url = subject.xpath('./a').attrib['href']

                meta = {
                    'program': program_name,
                    'subject': subject_name,
                }
                yield response.follow(subject_url, callback=self.parse_subject, meta=meta)

    def parse_subject(self, response):
        program = response.meta['program']
        subject = response.meta['subject']

        courses = response.xpath('//div[@id="programStreamCourses"]//tr/td')
        for course in courses:
            course_code = course.xpath('.//span[@class="courseCode"]/text()').get('')
            course_name = course.xpath('.//span[@class="title"]/text()').get('')
            course_url = course.xpath('./a').attrib['href']

            meta = {
                'program': program,
                'subject': subject,
                'course_code': course_code,
                'course_name': course_name,
            }
            yield response.follow(course_url, callback=self.parse_course, meta=meta)

    def parse_course(self, response):
        course_details = response.xpath('//form[@id="formCourseSearchDetails"]/div[contains(@id, "courseProfilePanel_")]')
        if not course_details:
            return False

        l = ItemLoader(WcsuwocaCourseItem(), response=response)
        l.default_output_processor = TakeFirst()

        l.add_value('institution_name', 'Western Continuing Studies')
        l.add_value('course_code', response.meta['course_code'])
        l.add_value('course_name', response.meta['course_name'])
        l.add_xpath('delivery_types', '//div[@class="courseProfileInstructionMethods"]/span[not(@class)]/span/text()')
        l.add_value('url', response.url)
        l.add_xpath('description', 'string(//div[@id="courseProfileOfficialCourseDescription"])')
        # l.add_value('subject', response.meta['subject'])
        l.add_value('subject', response.meta['program'])

        course_section = course_details.xpath('.//div[contains(@id, "courseSectionPanel_")]')
        if not course_section:
            return False
        course_data = course_section[0]

        # price = course_data.xpath('.//td[@class="tuitionProfileFees"]/text()').get()
        # price = course_data.xpath('.//tr[descendant::a[contains(., "Course")] and td[span[contains(., "") and @class="creditType" and contains(., "non-credit")]]]/td[@class="tuitionProfileFees"]/text()').get()
        price = course_data.xpath('.//td[@class="tuitionProfileFees"]/text()')
        if price:
            # prices = [p.strip().lstrip('$') for p in price.getall()]
            prices = list(map(lambda x: ', '.join(x), [re.findall(r'\d*\,?\d+\.\d{2}', p) for p in price.getall()]))
            prices = ', '.join(prices)
            prices = prices.split(', ')

            price = '0.0'
            for price_val in prices:
                try:
                    check_zerro_price = float(price_val.replace(',', ''))
                    if check_zerro_price:
                        price = price_val
                        break
                except ValueError:
                    continue

            # price = price.strip().lstrip('$')
        else:
            return False
            # price = '0.0'

        # # Skip courses with price $0.00
        # try:
        #     check_zerro_price = float(price.replace(',', ''))
        # except ValueError:
        #     check_zerro_price = False
        # if not check_zerro_price:
        #     return False
        l.add_value('price', [price])

        weekdays = course_data.xpath('string(.//div[contains(@class, "sectionScheduleMeetingDays")]//div[contains(@class, "content")])').get()
        if weekdays:
            weekdays = weekdays.strip()
            weekdays = re.sub(r'\s+', '', weekdays)
            weekdays = weekdays.split(',')
        else:
            weekdays = []
        l.add_value('days', [weekdays])
        # l.add_value('program', 'Continuing Education')
        # l.add_value('program', response.meta['program'])
        l.add_xpath('program', '//div[@id="courseProfileCertificates"]//li/a/text()')

        duration_hours_list = course_data.xpath('string(.//div[contains(@class, "section sectionScheduleMeetingTime")]//div[contains(@class, "content")])').get()
        if duration_hours_list:
            duration_hours_list = re.findall(r'\d{1,2}:\d{1,2}\w{2}', duration_hours_list)
            duration_hours_list = [t.lower() for t in duration_hours_list]
        else:
            duration_hours_list = []
        l.add_value('duration_hours', [duration_hours_list])
        l.add_value('duration_days_week', l.get_collected_values('days'))

        duration_month_list = course_data.xpath('string(.//div[contains(@class, "section sectionScheduleMeetingDates")]//div[contains(@class, "content")])').get()
        if duration_month_list:
            duration_month_list = re.findall(r'\w+\s\d{1,2},\s\d{4}', duration_month_list)
            if len(duration_month_list) == 2:
                duration_month_list = [datetime.strptime(d, '%b %d, %Y') for d in duration_month_list]

            if len(duration_month_list) == 1:
                duration_month_list = [datetime.strptime(duration_month_list[0], '%b %d, %Y')]
        else:
            duration_month_list = [None]
        l.add_value('duration_months', [duration_month_list])
        l.add_value('duration_as_string', [
            l.get_collected_values('duration_hours'),
            l.get_collected_values('duration_days_week'),
            l.get_collected_values('duration_months'),
        ])

        hours_site = course_data.xpath('string(.//div[contains(@class, "sectionContactHours")]//div[contains(@class, "content")])').get()
        if hours_site:
            hours_site = hours_site.strip()

        l.add_value('total_hours', [
            l.get_collected_values('duration_hours'),
            l.get_collected_values('duration_days_week'),
            hours_site,
        ])

        yield l.load_item()
