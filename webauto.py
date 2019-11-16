##@package webauto
# base class to be used as a prototype of web automation bots

from selenium import webdriver
from selenium.webdriver.firefox import options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import *

# captcha bypass service integration
from python_anticaptcha.tasks import ImageToTextTask
from python_anticaptcha.base import AnticaptchaClient

import  time
from    selenium.common.exceptions import TimeoutException
import  requests
import  urllib.request as req

from models import ResponseModel, CorpInfo, OfficerInfo, ReturnDocInfo
from bs4 import BeautifulSoup as bs
from lxml import etree

# detailed logging
import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

class Webauto():
    def __init__(self, _param=None):
        try:
            self.param = _param
            # normal chrome driver
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--headless")
            # chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
            chrome_options.add_argument("--start-maximized")
        except Exception as e:
            self.log_error("Failed to start the browser")
            self.browser = None

    def log_error(self, log):
        if self.param is not None and self.param.main_ui is not None:
            self.param.main_ui.log_err(log)

    def log_info(self, log):
        if self.param is not None and self.param.main_ui is not None:
            self.param.main_ui.log_info(log)

    ## create multilogin profile
    def create_profile(self):
        try:
            url = "https://api.multiloginapp.com/v2/profile"
            querystring = {
                "token":self.param.token,
                "screenWidthMin":600,
                "screenWidthMax":1920,
                "screenHeightMin":800,
                "screenHeightMax":1080}
            profile = Profile_v2(self.param)
            payload = str(profile)
            headers = {
                'Content-Type': "application/json",
                'Accept': "*/*",
                'Cache-Control': "no-cache",
                'Host': "api.multiloginapp.com",
                'Cookie': "__cfduid=70ccd9007338d6d81dd3b6271621b9cf9a97ea00",
                'Accept-Encoding': "gzip, deflate",
                'Content-Length': "848",
                'Connection': "keep-alive",
                'cache-control': "no-cache"
                }
            response = requests.request("POST", url, data=payload, headers=headers, params=querystring)
            if response.status_code != 200:
                return False

            ret = response.json()
            self.param.profile_id = ret['uuid'] 

            self.log_info("A new browser profile craeted")
            return True
        except Exception as e:
            self.log_error(str(e))
            return False

    ## remove multilogin profile
    def remove_profile(self):
        url = "https://api.multiloginapp.com/v1/profile/remove"
        querystring = {"token":self.param.token, 'profileId':self.param.profile_id}
        headers = {
            'Content-Type': "application/json",
            'Accept': "*/*",
            'Cache-Control': "no-cache",
            'Host': "api.multiloginapp.com",
            'Cookie': "__cfduid=70ccd9007338d6d81dd3b6271621b9cf9a97ea00",
            'Accept-Encoding': "gzip, deflate",
            'Content-Length': "848",
            'Connection': "keep-alive",
            'cache-control': "no-cache"
            }
        response = requests.request("POST", url, headers=headers, params=querystring)
        ret = response.json()
        if ret.status is not 'OK':
            return False
        else:
            self.param.profile_id = ret.value
            return True

    ## main work part - this is supposed to be abstract method. for now, just showing examples
    # Corporation search on Florida official site
    def work(self):
        try:
            url = "http://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults"
            payload = "inquiryType=EntityName&searchTerm=Shayne"
            headers = {
                'Content-Type': "application/x-www-form-urlencoded"
            }
            response = requests.request("GET", url, data=payload, headers=headers)
            soup = bs(response.text, 'html.parser')
            elems = soup.select('tbody tr')
            result = ResponseModel()
            result.Return_Count = len(elems)
            url = "http://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults"
            querystring = {
                'inquiryType':'EntityName',
                'searchTerm':'SMITH COMPANY, INC.'
            }

            headers = {
                'Content-Type': "application/x-www-form-urlencoded"
            }

            response = requests.request("GET", url, params=querystring, headers=headers)
            soup = bs(response.text, 'html.parser')
            elems = soup.select('tbody tr')
            
            for row in elems:
                elem = row.select_one('td a')
                if elem == None:
                    continue
                link = elem['href']
                entity_name = elem.text.strip()

                print(entity_name)
                corp = self.get_corp_FL('http://search.sunbiz.org/' + link)
                if corp is not None:
                    result.Return_Result.append(corp)
            result.Return_Count = len(result.Return_Result)
        except Exception as e:
            print(str(e))
            return False
        finally:
            self.quit_browser()

    ## get detailed corporation result from the detailed link
    # we just gets the page content and parse using bs4, this increases the speed much
    def get_corp_FL(self, url):
        try:
            corp = CorpInfo()

            headers = {
                'cache-control': "no-cache",
                }
            response = requests.request("GET", url, headers=headers)
            soup = bs(response.text, 'html.parser')

            try:
                elem = soup.find('div', {'class','detailSection corporationName'}).find_all('p')[0]
                corp.Entity_Type_Descr = elem.text.strip()
            except:
                pass

            try:
                elem = soup.find('div', {'class','detailSection corporationName'}).find_all('p')[1]
                corp.Entity_Name = elem.text.strip()
            except:
                pass

            try:
                elem = soup.find('span', text='Document Images').parent.select('td a')
                cnt = len(elem) // 2
                for i in range(cnt):
                    doc = ReturnDocInfo()
                    label = elem[i * 2].text
                    fields = label.split('--')
                    if len(fields) > 1:
                        doc.Return_Doc_Date = fields[0].strip()
                        doc.Return_Doc_Name = fields[1].strip()
                    else:
                        doc.Return_Doc_Name = fields[0].strip()
                    link = elem[i * 2]['href']
                    doc.Return_Doc = 'http://search.sunbiz.org' + link
                    corp.Return_Docs.append(doc)
            except:
                pass
            return corp
        except Exception as e:
            print(str(e))
            return None    

    ################################################################
    ## get base64 encoding of the image, this will be used as an input to the anticaptcha service
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

    ## solve image captcha, just a simple sample among various kinds of captchas
    def solve_img_captcha(self, img_path, xpath_result):
        try:
            api_key = 'xxxxxxxxxxxxxxxxxxxxxxxx'
            client = AnticaptchaClient(api_key)
            # img_b64 = self.get_base64_from_image(xpath_img)
            fp = open(img_path, 'rb')
            # task = ImageToTextTask(img_b64.encode("utf-8"))
            task = ImageToTextTask(fp)
            job = client.createTask(task)
            job.join()
            ret = ''
            while(ret == ''):
                ret = job.get_captcha_text()
                self.delay_me(3)
            self.set_value(xpath_result, ret)
            return True
        except Exception as e:
            print(str(e))
            return False

    ## google login
    def google_auth(self):
        self.log_info("[%s] Auth started. login=%s pass=%s"%(self.param.wid, self.param.login, self.param.password))
        self.navigate("https://accounts.google.com/Logout")
        self.navigate("https://accounts.google.com/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

        self.enter_text("//input[@id='Email']", self.param.login)
        self.click_element("//input[@id='next']")

        xpath = "//input[@id='Passwd']"
        self.wait_present(xpath, 5)
        self.delay_me(1)
        self.enter_text(xpath, self.param.password)
        xpath = "//input[@id='signIn']"
        self.wait_present(xpath, 5)
        self.click_element(xpath)
        self.delay_me(1)

        if self.is_element_present(xpath):
            self.log_info("[%s] Wrong password"%(self.param.wid))
            return False

        if "challenge" in self.browser.current_url:
            self.log_info("[%s] Recovery email asked"%(self.param.wid))
            xpath = '//*/div[text()="Confirm your recovery email"]'
            self.wait_present(xpath)
            self.click_element(xpath)
            xpath = "//*[@id=\"identifierId\"]"
            self.wait_present(xpath)
            self.delay_me(1)
            self.enter_text(xpath, self.param.recovery)
            xpath = "//*/div[@role=\"button\"]"
            self.click_element(xpath)
            self.delay(1)
            if "recovery-options" in self.browser.current_url:
                xpath = "//*/div[@role=\"button\"]"
                self.wait_present(xpath, 3)
                self.click_element(xpath)
                self.wait_unpresent(xpath, 3)
        
        self.delay_me(2)
        return True

    def close(self):
        if self.browser is not None:
            self.browser.quit()

    def __del__(self):
        pass
        # self.browser.quit()

    def switch_tab(self, idx):
        try:
            self.browser.switch_to.window(self.browser.window_handles[idx])
        except:
            return

    def new_tab(self, url = ''):
        try:
            self.browser.execute_script("window.open('%s','_blank');"%url)
        except:
            return

    def refresh(self):
        self.browser.refresh()

    def delay_me(self, timeout = 3):
        try:
            now = time.time()
            future = now + timeout
            while time.time() < future:
                pass
            return True
        except Exception as e:
            return False

    def delay(self, timeout = 3):
        self.browser.implicitly_wait(timeout)

    def occurence(self, xpath):
        try:
            elems = self.browser.find_elements_by_xpath(xpath)
            return len(elems)
        except:
            return 0

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
        try:
            now = time.time()
            future = now + timeout
            while time.time() < future:
                try:
                    target = self.browser.find_element_by_xpath(xpath)
                    if target is None:
                        return True
                except:
                    return True
            return False
        except Exception as e:
            self.log_error(str(e))(str(e))
            return False

    def navigate(self, url):        
        self.browser.get(url)

    def get_attribute(self, xpath, attr = 'value'):
        try:
            elem = self.browser.find_element_by_xpath(xpath)
            val = elem.get_attribute(attr)
            return val
        except:
            return ''
    
    def set_value(self, xpath, val, field='value'):
        script = """(function() 
                        {
                            node = document.evaluate("%s", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            if (node==null) 
                                return '';
                            node.%s='%s'; 
                            return 'ok';
                })()"""%(xpath,field,val)
        self.browser.execute_script(script)

    def click_element(self, xpath, timeout = 3, mode = 1):
        try:
            now = time.time()
            future = now + timeout
            while time.time() < future:
                target = self.browser.find_element_by_xpath(xpath)
                if target is not None:
                    if mode == 0:
                        target.click()
                    elif mode == 1:
                        js = """
                            xpath = "%s";
                            y=document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            y.click()
                            """%(xpath)
                        self.browser.execute_script(js)
                    return True
            return False
        except Exception as e:
            self.log_error(str(e))

    def middle_click(self, xpath, timeout = 3):
        js = """
            xpath = "%s";
            var mouseWheelClick = new MouseEvent('click', {'button': 1, 'which': 1 });
            y=document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            y.dispatchEvent(mouseWheelClick)
            """%(xpath)
        self.browser.execute_script(js)
    
    def expand_shadow_element(self, element):
        try:
            shadow_root = self.browser.execute_script('return arguments[0].shadowRoot', element)
            return shadow_root
        except Exception as e:
            self.log_error(str(e))
            return None

    def allow_popup(self):
        try:
            self.navigate("chrome://settings/content/popups")
            elem = self.browser.find_element_by_tag_name('settings-ui')
            sr = self.expand_shadow_element(elem)
            if sr is not None:
                elem = sr.find_element_by_id('main')              
                sr = self.expand_shadow_element(elem)
                if sr is not None:
                    elem = sr.find_element_by_css_selector('settings-basic-page')
                    sr = self.expand_shadow_element(elem)
                    if sr is not None:
                        elem = sr.find_element_by_css_selector('settings-privacy-page')
                        sr = self.expand_shadow_element(elem)
                        if sr is not None:
                            elem = sr.find_element_by_css_selector('category-default-setting')
                            sr = self.expand_shadow_element(elem)
                            if sr is not None:
                                elem = sr.find_element_by_id('toggle')
                                if elem is not None:
                                    elem.click()
        except Exception as e:
            self.log_error(str(e))

    def quit_browser(self):
        try:
            if self.browser is not None:
                self.browser.quit()
        except Exception as e:
            self.log_error(str(e))