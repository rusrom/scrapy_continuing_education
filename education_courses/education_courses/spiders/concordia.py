# -*- coding: utf-8 -*-
import scrapy
import re

from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, MapCompose
from education_courses.items import ConcordiaCourseItem


class ConcordiaSpider(scrapy.Spider):
    name = 'concordia'
    allowed_domains = ['concordia.ca']
    start_urls = ['https://www.concordia.ca/cce/courses.html']

    def parse(self, response):
        topics = response.xpath('//div[@class="card parbase section"]//a')
        for topic in topics:
            # yield response.follow(topic, callback=self.parse_courses)
            yield response.follow(topic, callback=self.parse_courses, dont_filter=True)

    def parse_courses(self, response):
        courses = response.xpath('//div[@class="offering-list section"]/div[@class="row"]//div[@class="title"]/a')
        program = response.xpath('//h1[contains(@class, "bold-large")]/text()').get()
        program = program.strip().lower().title() if program else 'No program'
        for course in courses:
            # yield response.follow(course, callback=self.parse_course, meta={'program': program})
            yield response.follow(course, callback=self.parse_course, meta={'program': program}, dont_filter=True)

    def parse_course(self, response):
        l = ItemLoader(item=ConcordiaCourseItem(), response=response)
        l.default_output_processor = TakeFirst()

        l.add_value('institution_name', 'Concordia University')
        l.add_xpath('course_code', '//div[@class="container"]//div[@class="ccode"]/text()')
        l.add_xpath('course_name', '//section[@id]//h1/text()')
        l.add_value('url', response.url)
        l.add_value('faculty', 'School of Continuing Studies')
        l.add_xpath('description', '//div[@class="container"]//span[@class="xlarge-text"]/div[@class="ccode"]/following-sibling::text()[normalize-space()]')
        l.add_value('location', '')
        l.add_value('subject', '')

        # get all blocks of course data
        course_data = response.xpath('//div[@class="course-section xlarge-text"]').getall()

        # get all prices
        prices = [re.search(r'\$([^\s]+)', block) for block in course_data]
        prices = [price.group(1) if price else '0.0' for price in prices]
        l.add_value('price', prices)

        # Get all days
        days_in_blocks = [re.findall(r'([\w ]+) +\(', block) for block in course_data]
        l.add_value('days', days_in_blocks)

        l.add_value('program', response.meta['program'])

        # # Get all courses time intervals
        time_in_blocks = [re.findall(r'\d{1,2}:\d{1,2}', block) for block in course_data]
        l.add_value('duration_hours', time_in_blocks)

        l.add_value('duration_days_week', l.get_collected_values('days'))

        l.add_xpath('duration_months', '//h3[@class="date burgundy"]/text()')
        l.add_value('duration_as_string', [
            l.get_collected_values('duration_hours'),
            l.get_collected_values('duration_days_week'),
            l.get_collected_values('duration_months'),
        ])

        hours_site = re.search(r'Duration[^\d]+(\d+)', course_data[0])
        if hours_site:
            hours_site = hours_site.group(1)
        else:
            hours_site = 0
        l.add_value('total_hours', [
            l.get_collected_values('duration_hours'),
            l.get_collected_values('duration_days_week'),
            hours_site,
        ])

        l.add_value('delivery_types', l.get_collected_values('duration_hours'))

        yield l.load_item()
