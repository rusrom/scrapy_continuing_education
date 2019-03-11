# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

from scrapy.exceptions import DropItem


class EducationCoursesPipeline(object):
    def process_item(self, item, spider):
        return item


class DuplicatesPipeline(object):

    def __init__(self):
        self.course_code_seen = set()

    def process_item(self, item, spider):
        if item['course_code'] in self.course_code_seen:
            raise DropItem("[-] Duplicate item found: {}".format(item))
        else:
            self.course_code_seen.add(item['course_code'])
            return item
