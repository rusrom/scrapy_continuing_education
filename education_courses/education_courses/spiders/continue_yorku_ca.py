# -*- coding: utf-8 -*-
import scrapy

from scrapy.loader import ItemLoader
from scrapy.loader.processors import MapCompose, TakeFirst
from education_courses.items import EducationCoursesItem

from scrapy.selector import Selector
# from scrapy.http import HtmlResponse

from selenium import webdriver
from time import sleep


CHROME_PATH = 'D:\\WebDrivers\\chromedriver.exe'


class ContinueYorkuCaSpider(scrapy.Spider):
    name = 'continue_yorku_ca'
    allowed_domains = ['yorku.ca']
    start_urls = ['https://continue.yorku.ca/york-scs/wp-admin/admin-ajax.php?interest=&format=&obtain=&action=scs_program_finder_search&paged=1']

    def parse(self, response):
        programs = response.xpath('//article[@class="program-listing"]//li/a')
        for program_link in programs[:1]:
            yield response.follow(program_link, callback=self.parse_program)

    def parse_program(self, response):        
        driver = webdriver.Chrome(CHROME_PATH)
        driver.get(response.url)
        driver.set_window_size(width=1600, height=1000)
        button = driver.find_element_by_xpath('//header//form[@class="cart"]/button[contains(text(), "Register")]')
        button.click()
        table_element = driver.find_element_by_xpath('//table[@class="shop_table cart"]/tbody')
        html_program_prices = table_element.get_attribute('outerHTML')
        driver.close()

        target_table_with_prices = Selector(text=html_program_prices)
        cart_rows = target_table_with_prices.xpath('//tr[1]/following-sibling::tr[@class="cart_item"]')

        program_prices = {}
        for row in cart_rows:
            course_code = row.xpath('string(./td[@class="product-name"])').get().strip().split()[0]
            course_price = row.xpath('string(./td[@class="product-price"])').get().strip().replace('$', '')
            program_prices[course_code] = course_price

        courses = response.xpath('//div[@class="program-course-list"]/h3')
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

    # def parse_program(self, response):
    #     courses = response.xpath('//div[@class="program-course-list"]/h3')
    #     for course in courses:
    #         l = ItemLoader(item=EducationCoursesItem(), selector=course)
    #         l.default_input_processor = MapCompose(lambda x: x.strip())
    #         l.default_output_processor = TakeFirst()

    #         l.add_value('institution_name', 'York University')
    #         l.add_xpath('course_code', './text()')
    #         l.add_xpath('course_name', './text()')
    #         l.add_xpath('description', './following-sibling::text()[2][normalize-space()]')
    #         l.add_value('program', response.xpath('//h1[@class="entry-title"]/text()').extract_first())
    #         l.add_value('subject', response.xpath('//h1[@class="entry-title"]/text()').extract_first())
    #         l.add_value('price', response.xpath('//header//p[@class="cohort-price"]/text()').extract_first())

    #         schedule = course.xpath('./following-sibling::div[@class="section group"]/div[strong[text()="Schedule:"]]/following-sibling::div[contains(text(), "From")]/text()[normalize-space()]').extract_first()
    #         l.add_value('days', schedule)
    #         l.add_value('duration_hours', schedule)
    #         l.add_value('duration_days_week', schedule)
    #         # l.add_value('duration_months', schedule) for debuging long string with schedule
    #         l.add_value('delivery_types', schedule)
    #         l.add_value('url', response.url)

    #         l.add_xpath('total_hours', './following-sibling::div/div[strong[contains(text(), "of Hours:")]]/following-sibling::div[1]/text()')
    #         # l.add_xpath('capacity', './following-sibling::div/div[strong[contains(text(), "of Classes:")]]/following-sibling::div[1]/text()')

    #         yield l.load_item()
