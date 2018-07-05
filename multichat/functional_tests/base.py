import os
import sys
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# create_session_cookie
from django.conf import settings
from django.contrib.auth import (
    SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY,
    get_user_model
)
from channels.testing import ChannelsLiveServerTestCase
from django.contrib.sessions.backends.db import SessionStore

SCREEN_DUMP_LOCATION = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'screendumps'
)

# Seconds to sleep in sleep method
DEFAULT_SLEEP = 0.25

# # Change browser driver here
BROWSER_DRIVER = 'Chrome'
# BROWSER_DRIVER = 'Firefox'
# BROWSER_DRIVER = 'Opera'

# # Change headless driver here
HEADLESS_DRIVER = None
# HEADLESS_DRIVER = 'browser'
# HEADLESS_DRIVER = 'pyvirtualdisplay'
# HEADLESS_DRIVER = 'xvfbwrapper'

# # Change headless backand here - used only by pyvirtualdisplay
HEADLESS_BACKEND = 'xvfb'
# HEADLESS_BACKEND = 'xephyr'


class Setup(ChannelsLiveServerTestCase):
    """ Initial setup methods for functional tests base class"""

    serve_static = True
    browser_driver = BROWSER_DRIVER
    headless_driver = HEADLESS_DRIVER

    @classmethod
    def setUpClass(cls):
        for arg in sys.argv:
            if 'liveserver' in arg:
                cls.server_url = 'http://' + arg.split('=')[1]
                return
        super().setUpClass()
        cls.server_url = cls.live_server_url

    def setUp(self):
        self.setup_platform()
        self.setup_headless()

        self.run_driver()

        if self.headless_driver == 'xvfbwrapper':
            self.addCleanup(self.browser.quit)

    def tearDown(self):
        if self.headless_driver not in (None, 'browser'):
            self.display.stop()

        if self._test_has_failed():
            if not os.path.exists(SCREEN_DUMP_LOCATION):
                os.makedirs(SCREEN_DUMP_LOCATION)
            for ix, handle in enumerate(self.browser.window_handles):
                self._windowid = ix
                self.browser.switch_to.window(handle)
                self.take_screenshot()
                self.dump_html()

        self.browser.quit()
        super().tearDown()

    def setup_platform(self):
        if self.browser_driver == 'Chrome':
            from selenium.webdriver.chrome.options import Options
            self.browser_class = webdriver.Chrome
            self.browser_options = Options()
            self.browser_options.add_argument("--disable-extensions")
            self.browser_options.add_argument("--no-sandbox")
            self.browser_options.add_argument("--no-default-browser-check")
            self.browser_options.add_argument("--no-first-run")
            self.browser_options.add_argument("--disable-default-apps")

        elif self.browser_driver == 'Firefox':
            self.browser_class = webdriver.Firefox
            self.firefox_profile = webdriver.FirefoxProfile()
            self.firefox_profile.set_preference(
                "browser.startup.homepage_override.mston‌​e", "ignore")
            self.firefox_profile.set_preference(
                "startup.homepage_welcome_url.additional‌​", "about:blank")
            self.firefox_profile.set_preference(
                'browser.shell.checkDefaultBrowser', False)
            self.firefox_profile.set_preference(
                'browser.download.folderList', 2)
            self.firefox_profile.set_preference(
                'browser.download.manager.showWhenStarting', False)
            self.firefox_profile.set_preference(
                'browser.helperApps.neverAsk.saveToDisk', 'text/csv')

        elif self.browser_driver == 'Opera':
            from selenium.webdriver.opera.options import Options
            self.opera_capabilities = DesiredCapabilities.OPERA
            self.opera_capabilities[
                'chromedriverExecutable'
            ] = '/home/balnir/opt/bin/operadriver'
            self.opera_capabilities['app'] = '/usr/bin/opera'
            self.browser_class = webdriver.Opera

    def setup_headless(self):
        if self.headless_driver is None:
            return False

        elif self.headless_driver is 'browser':
            if self.browser_driver == 'Chrome':
                self.browser_options.add_argument("--headless")
            elif self.browser_driver == 'Firefox':
                os.environ['MOZ_HEADLESS'] = '1'
            return False

        elif self.headless_driver == 'xvfbwrapper':
            from xvfbwrapper import Xvfb
            self.display = Xvfb(width=1600, height=1280, colordepth=16)
            self.addCleanup(self.display.stop)
            self.display.start()

        elif self.headless_driver == 'pyvirtualdisplay':
            from pyvirtualdisplay import Display
            self.display = Display(
                backend=HEADLESS_BACKEND, visible=0, size=(1600, 1280)
            )

        self.display.start()

    def run_driver(self):
        if self.browser_driver == 'Chrome':
            self.browser = self.browser_class(
                options=self.browser_options
            )

        elif self.browser_driver == 'Firefox':
            self.browser = self.browser_class(
                firefox_profile=self.firefox_profile
            )

        elif self.browser_driver == 'Opera':
            self.browser = self.browser_class(
                capabilities=self.opera_capabilities
            )

        self.browser.implicitly_wait(2)
        self.browser.set_window_size(1600, 1280)


class FunctionalTest(Setup):
    """Functional tests base class with attached helpers methods """

    def take_screenshot(self):
        filename = self._get_filename() + '.png'
        print('screenshotting to', filename)
        self.browser.get_screenshot_as_file(filename)

    def dump_html(self):
        filename = self._get_filename() + '.html'
        print('dumping page HTML to', filename)
        with open(filename, 'w') as f:
            f.write(self.browser.page_source)

    def _test_has_failed(self):
        for method, error in self._outcome.errors:
            if error:
                return True
        return False

    def _get_filename(self):
        timestamp = datetime.now().isoformat().replace(':', '.')[:19]
        return '{folder}/{clsname}.{method}-window{winid}-{timestamp}'.format(
            folder=SCREEN_DUMP_LOCATION,
            clsname=self.__class__.__name__,
            method=self._testMethodName,
            winid=self._windowid,
            timestamp=timestamp
        )

    def create_session_cookie(self, username, password):
        # First, create a new test user
        User = get_user_model()
        user = User.objects.create_user(username=username, password=password)

        # Then create the authenticated session using the new user credentials
        session = SessionStore()
        session[SESSION_KEY] = user.pk
        session[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0]
        session[HASH_SESSION_KEY] = user.get_session_auth_hash()
        session.save()

        # Finally, create the cookie dictionary
        cookie = {
            'name': settings.SESSION_COOKIE_NAME,
            'value': session.session_key,
            'secure': False,
            'path': '/',
        }
        return cookie

    def create_cookie_and_go_to_page(self, email):
        session_cookie = self.create_session_cookie(
            username=email, password='top_secret'
        )

        # visit some url in your domain to setup Selenium.
        # (404 pages load the quickest)
        self.browser.get(self.server_url)
        # self.browser.get(self.server_url + '/404.html')

        # add the newly created session cookie to selenium webdriver.
        self.browser.add_cookie(session_cookie)
        # refresh to exchange cookies with the server.
        self.browser.refresh()
        # This time user should present as logged in.
