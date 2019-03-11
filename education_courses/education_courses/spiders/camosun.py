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

            program_block_html_string = program_block.get()
            program_block_html_string = re.sub(r'^\s*<div>\s*', '', program_block_html_string)
            program_block_html_string = re.sub(r'\s*</div>\s*$', '', program_block_html_string)

            courses = program_block_html_string.split('<hr class="modest">')
            courses = [el for el in courses if el]

            for course_html in courses:

                course = Selector(text=course_html)
                l = ItemLoader(item=CamosunCourseItem())
                # l.default_input_processor = MapCompose(lambda x: x.strip())
                l.default_output_processor = Join(' | ')

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
                dates_data = []
                for ul in ul_blocks:
                    # Parse weekdays and times
                    ul_string = remove_tags(ul.get())
                    ul_string = re.sub(r'\s{2,}', ' ', ul_string)
                    ul_string = remove_garbage(ul_string)
                    ul_string = ul_string.strip()
                    ul_data.append(ul_string)

                    # Parse dates text node
                    date_string = ul.xpath('./preceding-sibling::text()[1]').get('')
                    date_string = remove_garbage(date_string)
                    # 1s check get we dates or just catch the bullets
                    if len(date_string) < 5:
                        date_string = ul.xpath('(./preceding-sibling::text()[2])').get('')
                        date_string = remove_garbage(date_string)
                    # Remove garbage till 2019
                    re_search = re.search(r'^(.+)2019', date_string)
                    if re_search:
                        remove_pattern = re.escape(re_search.group(1))
                        date_string = re.sub(remove_pattern, '', date_string)
                    # Write to list of dates only string that contains 2019
                    if '2019' in date_string:
                        dates_data.append(date_string.strip())

                prices = [re.search(r'\$(\d+)', p).group(1) if re.search(r'\$(\d+)', p) else '0.0' for p in ul_data if p]
                l.add_value('price', prices)
                # l.add_value('subject', ul_data)

                # Get strings weekdays
                # Remove string not containing time
                weekdays = [wd if re.search(r'\d+:\d+\w{2}', wd) else '' for wd in ul_data if wd]
                # Get string with weekday
                weekdays = [re.search(r'^[^\d]+', wd).group() if re.search(r'^[^\d]+', wd) else [] for wd in weekdays if wd]
                # Clear from bullets at the end of string
                weekdays = [re.sub(r'\W+$', '', i) for i in weekdays if i]
                # Clear from empty string after above clearing
                weekdays = [wd.split(' ') for wd in weekdays if wd]
                l.add_value('days', weekdays)
                l.add_value('program', program)

                # Get time in gropu like DD:DDam-DD:DDam
                duration_hours = [re.findall(r'(\d+:\d+\w{2}-\d+:\d+\w{2})', tm) for tm in ul_data if tm]
                # Plepare list for time like [['6:30pm', '9:30pm'], ['8:30am', '4:30pm']]
                # duration_hours = [tm[0].split('-') for tm in duration_hours if tm]
                duration_hours_list = []
                for tm in duration_hours:
                    if not tm:
                        continue
                    if len(tm) > 1:
                        for interval in tm:
                            duration_hours_list.append(interval.split('-'))
                    else:
                        duration_hours_list.append(tm[0].split('-'))

                l.add_value('duration_hours', duration_hours_list)
                l.add_value('duration_days_week', l.get_collected_values('days'))

                # Looking for month interval
                duration_month_list = []
                dur_month_tpl = '{year} {month}'
                for mon in dates_data:
                    if not mon:
                        continue
                    mon_res = re.search(r'(2019).+(\w{3} \d+) - (\w{3} \d+)?|(2019).+(\w{3} \d+)', mon)
                    if not mon_res:
                        continue
                    year, start_m, end_m, one_year, one_m = mon_res.groups()

                    if one_m:
                        m_start = dur_month_tpl.format(year=one_year, month=one_m)
                        m_end = dur_month_tpl.format(year=one_year, month=one_m)
                    else:
                        m_start = dur_month_tpl.format(year=year, month=start_m)
                        m_end = dur_month_tpl.format(year=year, month=end_m)

                    duration_month_list.append([m_start, m_end])

                l.add_value('duration_months', duration_month_list)
                l.add_value('duration_as_string', [
                    l.get_collected_values('duration_hours'),
                    l.get_collected_values('duration_days_week'),
                    l.get_collected_values('duration_months'),
                ])

                l.add_value('total_hours', [
                    l.get_collected_values('duration_hours'),
                    l.get_collected_values('duration_days_week'),
                ])

                # l.add_value('corequisites', dates_data)

                yield l.load_item()
