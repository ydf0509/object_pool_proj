import copy
import time
import typing
from urllib.error import URLError
import nb_log
import selenium
from selenium import webdriver
from selenium.common.exceptions import NoSuchWindowException
from selenium.webdriver import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import Chrome
from selenium.webdriver import PhantomJS

from universal_object_pool import ObjectPool, AbstractObject
from threadpool_executor_shrink_able import BoundedThreadPoolExecutor
import decorator_libs

"""
这个是池化 webdriver浏览器对象，可以同时用多个浏览器打开网页，比单个浏览器单线程循环调用driver快多了。
也比在多线程的函数内部频繁 driver实例化 和driver.quit()强很多。
"""


class WebDriverOperator(AbstractObject, nb_log.LoggerMixin):
    error_type_list_set_not_available = [NoSuchWindowException, URLError]

    # 如果出现了这些错误，会自动把对象标记为不可用，会重新生成。
    def __init__(self, driver_klass=webdriver.Chrome, is_open_picture=True, is_use_mobile_ua=False, is_use_headless=False, **selenium_driver_kwargs):
        self._is_open_picture = is_open_picture
        self._is_use_headless = is_use_headless
        self._is_use_mobile_ua = is_use_mobile_ua
        self._selenium_driver_kwargs = selenium_driver_kwargs
        if is_use_mobile_ua:
            self._ua = 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Mobile Safari/537.36'
        else:
            self._ua = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
        if driver_klass == webdriver.Chrome:
            driver = self._create_a_chrome_driver()
        elif driver_klass == webdriver.PhantomJS:
            driver = self._create_a_phantomjs_driver()
        else:
            raise ValueError(f'driver_klass 设置的不正确')
        self.core_obj = self.driver = driver

    def _create_a_chrome_driver(self):
        driver_path = ChromeDriverManager().install()  # webdriver_manager 包可以自动下载安装chrome驱动，比较方便，不需要自己指定路径。
        options = webdriver.ChromeOptions()
        # options.add_argument(r"user-data-dir=C:\Users\Administrator\AppData\Local\Google\Chrome\User Data")
        # add_argument()方法里填你Chrome浏览器保存Cookies的路径。
        options.add_experimental_option("excludeSwitches", ["ignore-certificate-errors"])
        # add_experimental_option()方法是访问https的网站，Selenium可能会报错，使用这个方法可以忽略报错。
        # driver.set_page_load_timeout(10)
        # driver.set_script_timeout(10)  # 这两种设置都进行才有效
        # driver.implicitly_wait(7)
        if self._is_use_headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')

        options.add_argument('--no-sandbox')
        options.add_argument(f'User-Agent={self._ua}')
        prefs = {
            'profile.default_content_setting_values': {
                # 'images': 2,  # 不加载图片
                'javascript': 1,  # 2不加载JS
                "User-Agent": self._ua}
        }
        options.add_experimental_option("prefs", prefs)
        if not self._is_open_picture:
            options.add_argument('--disable-images')
            options.add_argument('blink-settings=imagesEnabled=false')  # 这句禁用图片才能生效，上面两个禁用图片没起到效果。
        driver = webdriver.Chrome(driver_path, chrome_options=options, **self._selenium_driver_kwargs)
        driver.maximize_window()
        return driver

    def _create_a_phantomjs_driver(self):
        capabilities = DesiredCapabilities.PHANTOMJS.copy()
        capabilities['platform'] = "WINDOWS"
        capabilities['version'] = "10"
        capabilities['phantomjs.page.settings.loadImages'] = self._is_open_picture
        # capabilities['phantomjs.page.settings.userAgent'] = (
        #     "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) "
        #     "Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0")
        capabilities['phantomjs.page.settings.userAgent'] = self._ua
        capabilities['phantomjs.page.customHeaders.Accept-Language'] = 'zh-CN,zh;q=0.9,en;q=0.8'
        capabilities['phantomjs.page.customHeaders.Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        no_or_yes = 'yes' if self._is_open_picture else 'no'
        service_args = [f'--load-images={no_or_yes}', '--disk-cache=yes', '--ignore-ssl-errors=true']
        driver = webdriver.PhantomJS(desired_capabilities=capabilities, service_args=service_args, **self._selenium_driver_kwargs)
        return driver

    """ 下面3个是重写的方法"""

    def clean_up(self):  # 如果一个对象长时间内没被使用，那么对象池会自动将对象摧毁并从池中删除，会自动调用对象的clean_up方法。
        self.driver.quit()

    def before_back_to_queue(self, exc_type, exc_val, exc_tb):
        pass

    """以下可以自定义其他方法。
    因为设置了self.core_obj = self.driver ，父类重写了__getattr__,所以此对象自动拥有driver对象的所有方法,如果是同名同意义的方法不需要一个个重写。
    """


if __name__ == '__main__':
    driver_pool = ObjectPool(object_type=WebDriverOperator,
                             object_init_kwargs=dict(driver_klass=webdriver.Chrome, is_use_mobile_ua=False, ),
                             object_pool_size=2, max_idle_seconds=60)


    def test_open_page(url):
        with driver_pool.get(timeout=20) as driver:  # type: typing.Union[webdriver.Chrome,WebDriverOperator]
            driver.get(url)
            driver.save_screenshot(f'{int(time.time() * 1000)}.png')


    thread_pool = BoundedThreadPoolExecutor(20)
    with decorator_libs.TimerContextManager():
        for p in range(1, 10):
            urlx = f'https://www.autohome.com.cn/news/{p}/#liststart'
            thread_pool.submit(test_open_page, urlx)
            # thread_pool.submit(test_update_multi_threads_use_one_conn, x)
        thread_pool.shutdown()
    time.sleep(1000)
