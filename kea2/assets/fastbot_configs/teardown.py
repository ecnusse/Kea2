from uiautomator2 import Device
import time


class HybridTestCase:
    d: Device

PACKAGE_NAME = "it.feio.android.omninotes.alpha"
MAIN_ACTIVITY = "it.feio.android.omninotes.MainActivity"


def setUp(self: HybridTestCase):
    self.d.app_start(PACKAGE_NAME, MAIN_ACTIVITY)
    time.sleep(2)


def tearDown(self: HybridTestCase):
    self.d.app_stop(PACKAGE_NAME)