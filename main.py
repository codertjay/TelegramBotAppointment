import asyncio
import time
from datetime import datetime

import schedule
from decouple import config
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from webdriver_manager.chrome import ChromeDriverManager

from telegram_notification import send_message_on_telegram

BASE_URL = "https://appointment.bmeia.gv.at/?fromSpecificInfo=True"


class Appointment:
    def __init__(self, teardown=True):

        # Set up ChromeDriver service using the specified path
        s = Service(ChromeDriverManager().install())

        self.options = webdriver.ChromeOptions()
        self.options.add_argument('headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_experimental_option("detach", True)
        self.options.add_experimental_option("excludeSwitches", ['enable-logging'])

        # Use the specified service and options to create the Chrome WebDriver
        self.driver = webdriver.Chrome(options=self.options, service=s)

        self.detail_links = []
        self.page_detail_links = []
        self.driver.implicitly_wait(50)
        super(Appointment, self).__init__()

    def __enter__(self):
        self.driver.get(BASE_URL)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.teardown:
            self.driver.quit()

    def land_first_page(self):
        self.driver.get(BASE_URL)

    def click_on_state(self):
        # Locate the dropdown element using CSS selector
        office_dropdown = self.driver.find_element(by=By.CSS_SELECTOR, value='select[id="Office"]')

        # Use Select class to interact with dropdown
        office_selector = Select(office_dropdown)

        # Select "ABUJA" from the dropdown
        office_selector.select_by_visible_text('ABUJA')

        # Locate the "Next" button and click it
        next_button = self.driver.find_element(By.CSS_SELECTOR, 'input[value="Next"]')
        next_button.click()

    def click_on_reservation(self):
        # Locate the dropdown element for Reservation using CSS selector
        reservation_dropdown = self.driver.find_element(by=By.CSS_SELECTOR, value='select[id="CalendarId"]')

        # Use Select class to interact with dropdown
        reservation_selector = Select(reservation_dropdown)

        # Select "Visual Legalization" from the dropdown
        reservation_selector.select_by_visible_text('Verification /Legalization')

        # Locate the "Next" button and click it
        next_button = self.driver.find_element(By.CSS_SELECTOR, 'input[value="Next"]')
        next_button.click()

    def do_reservation(self):
        # Locate the dropdown element for PersonCount using CSS selector
        persons_dropdown = self.driver.find_element(by=By.CSS_SELECTOR, value='select[id="PersonCount"]')

        # Use Select class to interact with dropdown
        persons_selector = Select(persons_dropdown)

        # Select "1" from the dropdown for Number of Persons
        persons_selector.select_by_value('1')

        # Locate the "Next" button and click it
        next_button = self.driver.find_element(by=By.CSS_SELECTOR, value='input[value="Next"]')
        next_button.click()

    def click_next(self):
        # Locate the "Next" button and click it
        next_button = self.driver.find_element(by=By.CSS_SELECTOR, value='input[value="Next"]')
        next_button.click()

    def is_appointment_in_next_sixty_days(self, send_current_date=False):
        if send_current_date:
            oneHourMessage = f"\n For One Hour Time frame {datetime.now().time()}"
            asyncio.run(send_message_on_telegram(oneHourMessage))
        # Locate all table cells (td) containing the text "Week"
        week_cells = self.driver.find_elements(By.XPATH, '//td[contains(text(), "Week")]')

        # Iterate through each week cell and check if it falls within the next 60 days
        for week_cell in week_cells:
            try:
                # Extract the date range text from the current week cell
                date_range_text = week_cell.text.strip()

                # Extract start and end dates from the text
                start_date_str, end_date_str = date_range_text.split(' - ')
                start_date = datetime.strptime(start_date_str, 'Week %m/%d/%Y')
                end_date = datetime.strptime(end_date_str, '%m/%d/%Y')

                # Calculate the difference in days between the start date and today
                days_difference = (start_date - datetime.now()).days
                # Check if the start date is within the next 60 days
                if days_difference <= config("APPOINTMENT_DAYS", cast=int, default=60):
                    message = f"""
                        Appointment found between {start_date_str} and {end_date_str} in
                         {days_difference} days and current date is {datetime.now().strftime('%m/%d/%Y')}"""
                    asyncio.run(send_message_on_telegram(message))
                    return True
            except Exception as a:
                message = f"Error {a}"
                asyncio.run(send_message_on_telegram(message))

        # If no matching date range is found within the next 60 days
        return False


class AppointmentScheduler:
    def __init__(self):
        self.bot = Appointment(teardown=True)

    def run_appointment_process(self):
        try:
            print("running")
            self.bot.land_first_page()
            self.bot.click_on_state()
            self.bot.click_on_reservation()
            self.bot.do_reservation()
            self.bot.click_next()
            self.bot.is_appointment_in_next_sixty_days()
        except Exception as a:
            print(a)

    def run_one_hour_time(self):
        try:
            print("One hour time running")
            self.bot.is_appointment_in_next_sixty_days(send_current_date=True)
        except Exception as a:
            print(a)


# Create an instance of AppointmentScheduler
scheduler = AppointmentScheduler()

# Schedule the job to run every 5 minutes
schedule.every(1).minutes.do(scheduler.run_appointment_process)
schedule.every(1).hour.do(scheduler.run_one_hour_time)

while True:
    schedule.run_pending()
    time.sleep(1)
