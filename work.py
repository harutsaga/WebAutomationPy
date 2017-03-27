# Abstract web automation class
# 2019.09 David

import time
from selenium import webdriver
from selenium.webdriver.firefox import options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import *
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup as bs
import requests
import urllib.request as req

import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

import api.states.python_anticaptcha as anticap
ANTICAPTCHA_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxx'

class webauto_base():
    def __init__(self):
        pass

    # Start chrome browser for automation
    def start_browser(self):
        try:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            self.browser = webdriver.Chrome(executable_path='chromedriver', chrome_options = chrome_options)
            return True
        except Exception as e:
            # If the exception is related to the chrome version, try to download the latest chromedriver
            if 'Chrome version' in str(e):
                latest_ver = self.get_chrome_version()['windows']
                self.update_chromedriver(latest_ver)
            self.log_error(str(e))
            self.log_error("ERROR: Failed to start the browser")
            self.browser = None
            return False

    def get_chrome_version(self):
        url = "https://www.whatismybrowser.com/guides/the-latest-version/chrome"
        response = requests.request("GET", url)

        soup = bs(response.text, 'html.parser')
        rows = soup.select('td strong')
        version = {}
        version['windows'] = rows[0].parent.next_sibling.next_sibling.text
        version['macos'] = rows[1].parent.next_sibling.next_sibling.text
        version['linux'] = rows[2].parent.next_sibling.next_sibling.text
        version['android'] = rows[3].parent.next_sibling.next_sibling.text
        version['ios'] = rows[4].parent.next_sibling.next_sibling.text
        return version

    # logging helper functions
    def log_error(self, log):
        logging.error(log)

    def log_info(self, log):
        logging.info(log)

    # switch to the idx-th tab
    def switch_tab(self, idx):
        try:
            self.browser.switch_to.window(self.browser.window_handles[idx])
        except:
            return
    
    # open a new tab with url
    def new_tab(self, url = ''):
        try:
            self.browser.execute_script("window.open('%s','_blank');"%url)
        except:
            return

    # refresh the browser
    def refresh(self):
        self.browser.refresh()

