#!usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    ImageCaptchaSolver
    Author: Ali Toori, Python Developer [Bot Builder]
    Website: https://boteaz.com
    YouTube: https://youtube.com/@AliToori

"""

import csv
import os
import random
from pathlib import Path
from time import sleep
from datetime import datetime
from threading import Thread
from threading import Timer
from queue import Queue

import pandas as pd
import wget
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.speech_to_text_v1 import SpeechToTextV1
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import logging.config

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    'formatters': {
        'colored': {
            '()': 'colorlog.ColoredFormatter',  # colored output
            # --> %(log_color)s is very important, that's what colors the line
            'format': '[%(asctime)s] %(log_color)s[%(message)s]',
            'log_colors': {
                'DEBUG': 'green',
                'INFO': 'cyan',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            },
        },
        'simple': {
            'format': '[%(asctime)s] [%(message)s]',
        },
    },
    "handlers": {
        "console": {
            "class": "colorlog.StreamHandler",
            "level": "INFO",
            "formatter": "colored",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "simple",
            "filename": "AliImageCaptchaSolver_logs.log"
        },
    },
    "root": {"level": "INFO",
             "handlers": ["console", "file"]
             }
})
LOGGER = logging.getLogger()


class ImageCaptchaSolver:
    def __init__(self):
        self.logged_in_email = None
        self.logged_in = False
        self.driver = None
        self.PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
        self.file_account = str(self.PROJECT_ROOT / 'CMCRes/Accounts.csv')
        self.directory_downloads = str(self.PROJECT_ROOT / 'CMCRes/Downloads/')
        self.image_path = str(self.PROJECT_ROOT / 'CMCRes/Downloads/image.png')
        self.path_tesseract = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
        self.user_agents = self.get_user_agent()

    @staticmethod
    def enable_cmd_colors():
        # Enables Windows New ANSI Support for Colored Printing on CMD
        from sys import platform
        if platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    # Get random user agent
    def get_user_agent(self):
        file_uagents = str(self.PROJECT_ROOT / 'CMCRes/user_agents.txt')
        with open(file_uagents) as f:
            content = f.readlines()
        u_agents_list = [x.strip() for x in content]
        return u_agents_list

    # Get web driver
    def get_driver(self, headless=False):
        LOGGER.info(f'Launching chrome driver')
        DRIVER_BIN = str(self.PROJECT_ROOT / 'CMCRes/bin/chromedriver.exe')
        service = Service(executable_path=DRIVER_BIN)
        # user_dir = str(self.PROJECT_ROOT / 'CMCRes/UserData')
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument("--single-process")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument('--no-sandbox')
        options.add_argument('--incognito')
        options.add_argument('--disable-extensions')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors')
        # options.add_argument(f"--user-data-dir={user_dir}")
        options.add_experimental_option('prefs', {
            'directory_upgrade': True,
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            f'profile.default_content_settings.popups': False,
            f'download.default_directory': f'{self.directory_downloads}'})
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
        if headless:
            options.add_argument('--headless')
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    @staticmethod
    def wait_until_visible(driver, xpath=None, element_id=None, name=None, class_name=None, tag_name=None, css_selector=None, duration=10000, frequency=0.01):
        if xpath:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.XPATH, xpath)))
        elif element_id:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.ID, element_id)))
        elif name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.NAME, name)))
        elif class_name:
            WebDriverWait(driver, duration, frequency).until(
                EC.visibility_of_element_located((By.CLASS_NAME, class_name)))
        elif tag_name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.TAG_NAME, tag_name)))
        elif css_selector:
            WebDriverWait(driver, duration, frequency).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))

    # Voice to text Converter
    def get_text_from_speech(self, driver):
        apikey = 'fsdfsdfsdfs'
        url = 'https://api.us-south.speech-to-text.watson.cloud.ibm.com/instances/'
        # Setup Service
        authenticator = IAMAuthenticator(apikey)
        stt = SpeechToTextV1(authenticator=authenticator)
        stt.set_service_url(url)
        wait_until_visible(driver=driver, class_name='rc-audiochallenge-tdownload-link', duration=5)
        challange_audio_link = driver.find_element_by_class_name('rc-audiochallenge-tdownload-link').get_attribute('href')
        wget.download(challange_audio_link, "voice.mp3")
        # Perform conversion
        with open('voice.mp3', 'rb') as f:
            res = stt.recognize(audio=f, content_type='audio/mp3', model='en-US_NarrowbandModel').get_result()
        text = res['results'][0]['alternatives'][0]['transcript']
        for file in os.listdir(self.directory_downloads):
            if file.endswith('.mp3'):
                os.remove(f'{os.getcwd()}\\{file}')
        return text

    # Captcha solver
    def solve_captcha(self):
        try:
            i_frame_elem = driver.find_element(By.XPATH, '(//*[@title="reCAPTCHA"])[1]')
            self.driver.switch_to.frame(i_frame_elem)
            self.driver.find_element(By.ID, 'recaptcha-anchor').click()
            sleep(1)
            self.driver.switch_to.default_content()
            wait_until_visible(driver=driver, xpath='//*[@title="recaptcha challenge"]', duration=3)
            frame = self.driver.find_element(By.XPATH, '//*[@title="recaptcha challenge"]')
            self.driver.switch_to.frame(frame)
            wait_until_visible(driver=driver, element_id='recaptcha-audio-button', duration=3)
            self.driver.find_element(By.ID, 'recaptcha-audio-button').click()
            text = get_text_from_speech(driver=driver)
            print(f"reCaptcha text: {text}")
            wait_until_visible(driver=driver, element_id='audio-response', duration=3)
            self.driver.find_element(By.ID, 'audio-response').send_keys(text)
            wait_until_visible(driver=driver, element_id='recaptcha-verify-button', duration=3)
            self.driver.find_element(By.ID, 'recaptcha-verify-button').click()
            self.driver.switch_to.default_content()
        except:
            pass

    def main(self):
        freeze_support()
        self.enable_cmd_colors()
        # Print ASCII Art
        print('************************************************************************\n')
        pyfiglet.print_figlet('____________                   ImageCapctchaSolver ____________\n', colors='RED')
        print('Author: Ali Toori, Bot Developer\n'
              'Website: https://boteaz.com/\n************************************************************************')
        LOGGER.info(f'ImageCapctchaSolver launched')
        if self.driver is None:
            self.driver = self.get_driver()
            self.solve_captcha()


if __name__ == '__main__':
    bet_bot = CMCBot()
    bet_bot.main()
