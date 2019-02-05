# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import FormRequest
from scrapy.selector import Selector
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, MapCompose
from education_courses.items import EducationCoursesItem


class CheckFormRequestSpider(scrapy.Spider):
    name = 'check_form_request'
    allowed_domains = ['yorku.ca']
    start_urls = ['https://continue.yorku.ca/york-scs/wp-admin/admin-ajax.php?interest=&format=&obtain=&action=scs_program_finder_search&paged=1']

    def parse(self, response):
        programs = response.xpath('//article[@class="program-listing"]//li/a')
        for i, program_link in enumerate(programs[:5]):
            yield response.follow(program_link, callback=self.parse_program, meta={'cookiejar': i})

    def parse_program(self, response):
        # html_program = response.body
        program_html = response.text

        yield FormRequest.from_response(response=response, formxpath='//header//form[@class="cart"]', callback=self.parse_cart, dont_filter=True, meta={
            'cookiejar': response.meta['cookiejar'],
            'program_html': program_html,
            'program': response.xpath('//meta/following-sibling::title/text()').extract_first()
        })

    def parse_cart(self, response):
        # Get prices from cart
        cart_rows = response.xpath('//tr[1]/following-sibling::tr[@class="cart_item"]')
        program_prices = {}
        for row in cart_rows:
            course_code = row.xpath('string(./td[@class="product-name"])').get().strip().split()[0]
            course_price = row.xpath('string(./td[@class="product-price"])').get().strip().replace('$', '')
            program_prices[course_code] = course_price

        # Block with all courses info
        program_html = Selector(text=response.meta['program_html'])
        courses = program_html.xpath('//div[@class="program-course-list"]/h3')

        for course in courses:
            l = ItemLoader(item=EducationCoursesItem(), selector=course)
            l.default_input_processor = MapCompose(lambda x: x.strip())
            l.default_output_processor = TakeFirst()

            l.add_value('institution_name', 'York University')
            l.add_xpath('course_code', './text()')
            l.add_xpath('course_name', './text()')
            l.add_xpath('description', './following-sibling::text()[2][normalize-space()]')
            l.add_value('program', response.xpath('//h1[@class="entry-title"]/text()').extract_first())
            # l.add_value('subject', response.xpath('//h1[@class="entry-title"]/text()').extract_first())
            l.add_value('price', program_prices.get(l.get_collected_values('course_code')[0]))

            schedule = course.xpath('./following-sibling::div[@class="section group"]/div[strong[text()="Schedule:"]]/following-sibling::div[contains(text(), "From")]/text()[normalize-space()]').extract_first()
            l.add_value('days', schedule)
            l.add_value('duration_hours', schedule)
            l.add_value('duration_days_week', schedule)
            l.add_value('duration_months', schedule)
            l.add_value('delivery_types', schedule)
            l.add_value('url', response.url)
            l.add_value('faculty', 'School of Continuing Studies')

            # l.add_xpath('total_hours', './following-sibling::div/div[strong[contains(text(), "of Hours:")]]/following-sibling::div[1]/text()')
            l.add_value('total_hours', [l.get_collected_values('duration_hours')[0], l.get_collected_values('duration_days_week')[0]])

            l.add_value('duration_as_string', [
                l.get_output_value('duration_hours'),
                l.get_output_value('duration_days_week'),
                l.get_output_value('duration_months'),
            ])

            # l.add_xpath('capacity', './following-sibling::div/div[strong[contains(text(), "of Classes:")]]/following-sibling::div[1]/text()')

            yield l.load_item()
