import re
import csv
import os.path

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from time import sleep
from parsel import Selector
from w3lib.html import replace_escape_chars
from datetime import datetime


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = 'result_yorku_ca_courses.csv'
CSV_FILE_PATH = os.path.join(ROOT_DIR, CSV_FILE)
CSV_FILE_FIELDNAMES = [
    'institution_name', 'course_code', 'course_name', 'delivery_types', 'url',
    'faculty', 'description', 'location', 'subject', 'price', 'duration_as_string',
    'days', 'prerequisite', 'capacity', 'corequisites', 'program', 'total_hours',
    'duration_hours', 'duration_days_week', 'duration_months'
]

CHROME_PATH = 'D:\\WebDrivers\\chromedriver.exe'
start_url = 'https://continue.yorku.ca/york-scs/wp-admin/admin-ajax.php?interest=&format=&obtain=&action=scs_program_finder_search&paged=1'


def write_to_csv(data):
    if os.path.exists(CSV_FILE_PATH):
        write_headers = False
    else:
        write_headers = True

    with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8') as f:
        csv_writer = csv.DictWriter(f, fieldnames=CSV_FILE_FIELDNAMES)
        if write_headers:
            csv_writer.writeheader()
        csv_writer.writerow(data)


def make_clear_string(val):
    val = replace_escape_chars(val)
    val = re.sub(r'\s{2,}', ' ', val)
    return val.strip()


def start_webdriver():
    driver = webdriver.Chrome(CHROME_PATH)
    driver.set_window_size(1600, 1024)
    return driver


# Get weekdays: Thursday,Sunday
def get_week_days(val):
    weekdays = re.findall(r'(Sunday-[^ ]+|Monday-[^ ]+|Tuesday-[^ ]+|Wednesday-[^ ]+|Thursday-[^ ]+|Friday-[^ ]+|Saturday-[^ ]+|Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)', val)
    weekdays_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    if weekdays and '-' in weekdays[0]:
        start_day, end_day = weekdays[0].replace(',', '').split('-')
        weekdays = weekdays_list[weekdays_list.index(start_day):weekdays_list.index(end_day) + 1]
    weekdays = ', '.join(weekdays)
    return weekdays

# # Get weekdays: Thursday,Sunday
# def get_week_days(val):
#     # weekdays = re.findall(r'([A-Za-z]+)\s*\d+:\d+\w{,2}', val)
#     val = ', '.join(weekdays)
#     return val


def get_duration_hours(val):
    intervals = re.findall(r'(\d+:\d+\w{2})', val)
    if intervals:
        if len(intervals) > 2:
            result = []
            # We have several timeintervals
            # Get by couple time intervals from intervals
            for start_time, end_time in zip(intervals[::2], intervals[1::2]):
                start_time = datetime.strptime(start_time, '%I:%M%p')
                end_time = datetime.strptime(end_time, '%I:%M%p')
                duration_hours = (end_time - start_time).seconds / 3600
                result.append(duration_hours)
            min_duration = min(result)
            max_duration = max(result)
        else:
            # we have 1 timeinterval
            start_time, end_time = intervals
            start_time = datetime.strptime(start_time, '%I:%M%p')
            end_time = datetime.strptime(end_time, '%I:%M%p')
            duration_hours = (end_time - start_time).seconds / 3600
            min_duration = duration_hours
            max_duration = duration_hours
    else:
        min_duration = 0.0
        max_duration = 0.0

    val = [min_duration, max_duration]
    return val


# Get duration days of week: [2.0, 2.0]
def get_duration_days_week(val):
    if val:
        weekdays = val.split(', ')
        count = float(len(weekdays))
    else:
        count = float(0)
    val = [count, count]
    return val


def get_duration_month(val):
    dates = re.findall(r'\d+-\w+-\d+', val)
    start_date, end_date = dates[:2]
    start_date = datetime.strptime(start_date, '%d-%b-%Y')
    end_date = datetime.strptime(end_date, '%d-%b-%Y')
    duration_days = round((end_date - start_date).days / 30, 2)
    val = [duration_days, duration_days]
    return val


def get_delivery_types(val, duration_hours):
    if sum(duration_hours):
        delivery_type = re.search(r'(Onsite|Offsite)', val)
        if delivery_type:
            delivery_type = delivery_type.group()
            val = delivery_type.replace('Onsite', 'In Class').replace('Offsite', 'Online')
        else:
            val = ''
    else:
        val = 'Blended'
    return val


def get_total_hours(duration_hours, duration_days_week, of_hours):
    if sum(duration_hours):
        val = list(map(lambda x, y: x * y, duration_hours, duration_days_week))
    else:
        val = of_hours.strip()
        try:
            of_hours = round(float(val), 2)
        except ValueError:
            of_hours = 0.0
        val = [of_hours, of_hours]
    return val


def get_prices(val):
    # Remove comma as thousand separator
    val = val.replace(',', '')
    try:
        price = round(float(val), 2)
    except ValueError:
        price = 0.0
    val = [price, price]
    return val


def go_program(driver, program_url):
    driver.get(program_url)
    # Get program name for all courses
    try:
        program = driver.find_element_by_xpath('//h1[@class="entry-title"]').text.strip()
        # program = re.sub(r'\s+\|.+$', '', program)
    except NoSuchElementException:
        program = ''

    # Pull courses HTML markup to parsel
    try:
        element_targets_list = driver.find_element_by_xpath('//div[@class="entry-content"]//div[@class="program-course-list"]')
    except NoSuchElementException:
        print('!!!!!!!!!!!!!!!!!!  NO COURSES LIST !!!!!!!!!!!!!!!!!!!!')
        return False

    html_targets_list = element_targets_list.get_attribute('innerHTML')
    sel = Selector(text=html_targets_list)

    # Scrape information about ech course
    targets = sel.xpath('//h3')
    all_courses = []
    for target in targets:
        data = {}
        data['institution_name'] = 'York University'

        course_name = target.xpath('./text()').get('')
        # data['course_code'] = course_name.strip().split()[0] if course_name else ''
        try:
            course_code = re.search(r'^\w+\s?/?\d+', course_name).group()
        except AttributeError:
            course_code = ''
        data['course_code'] = course_code

        # data['course_name'] = ' '.join(course_name.split()[1:]) if course_name else ''

        data['course_name'] = course_name.replace(data['course_code'], '').strip() if course_name else ''

        course_description = target.xpath('./following-sibling::text()[2][normalize-space()]').get()
        data['description'] = course_description.strip() if course_description else ''
        data['program'] = program

        schedule = target.xpath('./following-sibling::div[@class="section group"]/div[strong[text()="Schedule:"]]/following-sibling::div[contains(text(), "From")]/text()[normalize-space()]').getall()
        if schedule:
            schedule = ' '.join(schedule[:2])
            schedule = make_clear_string(schedule)
        else:
            schedule = ''

        data['days'] = get_week_days(schedule)
        data['duration_hours'] = get_duration_hours(schedule)
        data['duration_days_week'] = get_duration_days_week(data['days'])
        data['duration_months'] = get_duration_month(schedule)
        data['delivery_types'] = get_delivery_types(schedule, data['duration_hours'])
        data['url'] = driver.current_url
        data['faculty'] = 'School of Continuing Studies'

        of_hours = target.xpath('./following-sibling::div/div[strong[contains(text(), "# of Hours")]]/following-sibling::div/text()').get()
        data['total_hours'] = get_total_hours(data['duration_hours'], data['duration_days_week'], of_hours)
        data['duration_as_string'] = '{0} hrs/day, {1} days/week for {2} months'.format(
            data['duration_hours'],
            data['duration_days_week'],
            data['duration_months'],
        )

        # Collect info all courses in program
        all_courses.append(data)

        print(data)
    print('-----------------------')

    # Get prices inside cart
    try:
        # register_button = driver.find_element_by_xpath('//header//form[@class="cart"]/button[@type="submit" and contains(text(), "Register")]')
        register_button = driver.find_element_by_xpath('(//button[@type="submit" and contains(text(), "Register")]|//a[@title="Apply" and contains(text(), "Apply")])')
    except NoSuchElementException:
        print('!!!!!!!!!!! NO BUTTON REGISTER/APPLY !!!!!!!!!!!!!!')
        return False

    register_button.click()

    # Scrape course prices
    element_cart_table = driver.find_element_by_xpath('//table[@class="shop_table cart"]')
    html_cart_table = element_cart_table.get_attribute('innerHTML')
    selector_cart_table = Selector(text=html_cart_table)

    cart_rows = selector_cart_table.xpath('//tbody/tr[td[@class="product-price"] and not(contains(string(), "$0.0"))]')
    program_prices = {}
    for row in cart_rows:
        cart_course_name = row.xpath('string(./td[@class="product-name"])').get('')
        try:
            course_code = re.search(r'^\w+\s?/?\d+', cart_course_name.strip()).group()
        except AttributeError:
            course_code = ''
        course_code = course_code.strip()
        course_price = row.xpath('string(./td[@class="product-price"])').get('').strip().replace('$', '')
        program_prices[course_code] = course_price

    # Adding prices to courses
    # for data in all_courses:
    #     data['price'] = get_prices(program_prices.get(data['course_code'], ''))
    #     write_to_csv(data)
    #     print('Course data was writed to csv!')

    program_prices_for_empty_codes = list(program_prices.items())
    for data in all_courses:
        if data['course_code']:
            # If CODE is already scraped
            data['price'] = get_prices(program_prices.get(data['course_code'], ''))
        else:
            # Fill empty CODE and PRICE
            try:
                data['course_code'], data['price'] = program_prices_for_empty_codes.pop(0)
                data['price'] = get_prices(data['price'])
            except IndexError:
                data['price'] = [0.0, 0.0]

        write_to_csv(data)
        print('Course data was writed to csv!')

    driver.delete_all_cookies()


def start_university_scraping(driver):
    # Check next page
    try:
        next_page = driver.find_element_by_xpath('//div[contains(@class, "pagination")]//a[contains(text(), "Next")]')
        next_page_url = next_page.get_attribute('href')
    except NoSuchElementException:
        next_page_url = False

    # Start parsing page with list of programs
    programs = driver.find_elements_by_xpath('//article[@class="program-listing"]//li/a')
    programs_urls = [a.get_attribute('href') for a in programs]

    # Scraping program
    for program_url in programs_urls:
        driver.delete_all_cookies()
        go_program(driver, program_url)

    # # Go next page
    if next_page_url:
        driver.delete_all_cookies()
        print('>>>>>>>>>>>>>>>>>> TO NEXT PAGE >>>>>>>>>>>>>>>>>>>>')
        driver.get(next_page_url)
        # Recursion while next page exists
        start_university_scraping(driver)
    else:
        driver.close()


driver = start_webdriver()
driver.get(start_url)
start_university_scraping(driver)
