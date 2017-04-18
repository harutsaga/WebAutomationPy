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

    # wait for <timeout> seconds
    def delay_me(self, timeout = 3):
        try:
            now = time.time()
            future = now + timeout
            while time.time() < future:
                pass
            return True
        except Exception as e:
            return False

    # let the browser to wait for <timeout> seconds
    def delay(self, timeout = 3):
        self.browser.implicitly_wait(timeout)
        
    # number of occurences for specified xpath
    def occurence(self, xpath):
        try:
            elems = self.browser.find_elements_by_xpath(xpath)
            return len(elems)
        except:
            return 0

    # get base64 encoding of image from xpath
    def get_base64_from_image(self, xpath_img):
        try:
            js = """
                xpath="%s";
                img=document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;             ;
                var canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                var ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                var dataURL = canvas.toDataURL('image/png');
                return dataURL.replace(/^data:image\/(png|jpg);base64,/, '');
                """%(xpath_img)
            res = self.browser.execute_script(js)
            return res
        except Exception as e:
            print(js)
            print(str(e))
            return ''

    # solve image-captcha automatically and return the result
    def solve_img_captcha(self, img_path, xpath_result):
        global ANTICAPTCHA_KEY
        try:
            api_key = ANTICAPTCHA_KEY
            client = anticap.AnticaptchaClient(api_key)
            fp = open(img_path, 'rb')
            task = anticap.ImageToTextTask(fp)
            job = client.createTask(task)
            job.join()
            ret = ''
            while(ret == ''): # wait for the solve job to be finished
                ret = job.get_captcha_text()
                self.delay_me(1)
            self.set_value(xpath_result, ret)
            return True
        except Exception as e:
            print('solving captcha failed:' + str(e))
            return False

    # check if there is an element in the specified xpath
    def is_element_present(self, xpath):
        try:
            elem = self.browser.find_element_by_xpath(xpath)
            if elem is None:
                return False
            return True
        except:
            return False

    def enter_text(self, xpath, value, timeout = 3, manual = True):
        try:
            now = time.time()
            future = now + timeout
            while time.time() < future:
                target = self.browser.find_element_by_xpath(xpath)
                if target is not None:
                    if manual:
                        target.send_keys(Keys.CONTROL + "a")
                        target.send_keys(value)
                        break
                    else:
                        js = "arguments[0].value = '%s'" % (value)
                        self.browser.execute_async_script(js, target)
            return True
        except Exception as e:
            self.log_error(str(e))
            return False

    def wait_present(self, xpath, timeout = 2):
        try:
            now = time.time()
            future = now + timeout
            while time.time() < future:
                try:
                    target = self.browser.find_element_by_xpath(xpath)
                    if target is not None:
                        return True
                except:
                    pass
            return False
        except Exception as e:
            self.log_error(str(e))(str(e))
            return False

    def wait_unpresent(self, xpath, timeout = 3):
