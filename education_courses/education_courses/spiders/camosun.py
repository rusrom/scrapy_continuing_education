# -*- coding: utf-8 -*-
import scrapy
import re

from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, MapCompose, Join
from scrapy.selector import Selector

from education_courses.items import CamosunCourseItem
from w3lib.html import replace_escape_chars, replace_entities, remove_tags


def remove_garbage(val):
    val = replace_escape_chars(val)
    val = replace_entities(val)
    val = re.sub(r'\s{2,}', ' ', val)
    return val.strip()


class CamosunSpider(scrapy.Spider):
    name = 'camosun'
    allowed_domains = ['camosun.ca']
    start_urls = ['http://camosun.ca/ce/programs.html']

    def parse(self, response):
        programs = response.xpath('//h2/a')
        for program_url in programs:
            faculty = program_url.xpath('./text()').get()
            yield response.follow(program_url, meta={'faculty': faculty}, callback=self.parse_program)

    def parse_program(self, response):
        programs = response.xpath('//div[h2[@id]]')
        for program_block in programs:
            program = program_block.xpath('./h2/text()').get()

            program_block_html_string = ''.join(program_block.xpath('./child::*').extract())
            print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>', program_block.extract(), '<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
            courses = program_block_html_string.split('<hr class="modest">')
            courses = [el for el in courses if el]

            for course_html in courses:
                # print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>', course_html, '<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
                course = Selector(text=course_html)
                l = ItemLoader(item=CamosunCourseItem())
                l.default_input_processor = MapCompose(lambda x: x.strip())
                l.default_output_processor = Join()

                course = course.xpath('//h3[@id and not(following-sibling::p[contains(@class, "alert-info")]) and not(following-sibling::del)]')
                # If in block tere is no matching h3 element skip this element
                if not course:
                    continue

                l.add_value('institution_name', 'Camosun College')
                l.add_value('course_code', course.xpath('./@id').get())
                l.add_value('course_name', course.xpath('./text()').get())
                l.add_value('delivery_types', 'Onsite')
                l.add_value('url', response.url)
                l.add_value('faculty', response.meta['faculty'])
                l.add_value('description', course.xpath('./following-sibling::p[1]//text()').getall())

                ul_blocks = course.xpath('./following-sibling::ul[contains(string(), "$")]')

                # Skip course if no ul block with days and price
                if not ul_blocks:
                    continue

                ul_data = []
                for ul in ul_blocks:
                    ul_string = remove_tags(ul.get())
                    ul_string = re.sub(r'\s{2,}', ' ', ul_string)
                    ul_string = ul_string.strip()
                    ul_data.append(ul_string)

                l.add_value('price', ul_data)
                l.add_value('program', program)

                yield l.load_item()
