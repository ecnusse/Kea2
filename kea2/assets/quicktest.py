import unittest
import uiautomator2 as u2

from time import sleep
from kea2 import precondition, prob, KeaTestRunner, Options
from kea2.u2Driver import U2Driver


class Omni_Notes_Sample(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect() 
    
    @prob(0.2)
    @precondition(
        lambda self: self.d(description="Navigate up").exists
    )
    def test_goBack(self):
        print("Navigate back")
        self.d(description="Navigate up").click()
        sleep(0.5)
    
    @prob(0.2)
    @precondition(
        lambda self: self.d(description="drawer closed").exists
    )
    def test_openDrawer(self):
        print("Open drawer")
        self.d(description="drawer closed").click()
        sleep(0.5)

    @prob(0.5)  # The probability of executing the function when precondition is satisfied.
    @precondition(
        lambda self: self.d(text="Omni Notes Alpha").exists
        and self.d(text="Settings").exists
    )
    def test_goToPrivacy(self):
        """
        The ability to jump out of the UI tarpits

        precond:
            The drawer was opened
        action:
            go to settings -> privacy
        """
        print("trying to click Settings")
        self.d(text="Settings").click()
        sleep(0.5)
        print("trying to click Privacy")
        self.d(text="Privacy").click()

    @precondition(
        lambda self: self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists
    )
    def test_rotation(self):
        """
        The ability to make assertion to find functional bug

        precond:
            The search input box is opened
        action:
            rotate the device (set it to landscape, then back to natural)
        assertion:
            The search input box is still being opened
        """
        print("rotate the device")
        self.d.set_orientation("l")
        sleep(2)
        self.d.set_orientation("n")
        sleep(2)
        assert self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists()


URL = "https://github.com/federicoiosue/Omni-Notes/releases/download/6.2.0_alpha/OmniNotes-alphaRelease-6.2.0.apk"
FALL_BACK_URL = "https://gitee.com/XixianLiang/Kea2/raw/main/omninotes.apk"
PACKAGE_NAME = "it.feio.android.omninotes.alpha"
FILE_NAME = "omninotes.apk"


def download_omninotes():
    import socket
    socket.setdefaulttimeout(30)
    try:
        import urllib.request
        urllib.request.urlretrieve(URL, FILE_NAME)
    except Exception as e:
        print(f"[WARN] Download from {URL} failed: {e}. Try to download from fallback URL {FALL_BACK_URL}", flush=True)
        try:
            urllib.request.urlretrieve(FALL_BACK_URL, FILE_NAME)
        except Exception as e2:
            print(f"[ERROR] Download from fallback URL {FALL_BACK_URL} also failed: {e2}", flush=True)
            raise e2


def check_installation(serial=None):
    import os
    from pathlib import Path
    
    d = u2.connect(serial)
    # automatically install omni-notes
    if PACKAGE_NAME not in d.app_list():
        if not os.path.exists(Path(".") / FILE_NAME):
            print(f"[INFO] omninote.apk not exists. Downloading from {URL}", flush=True)
            download_omninotes()
        print("[INFO] Installing omninotes.", flush=True)
        d.app_install(FILE_NAME)
    d.stop_uiautomator()


if __name__ == "__main__":
    check_installation(serial=None)
    KeaTestRunner.setOptions(
        Options(
            driverName="d",
            Driver=U2Driver,
            packageNames=[PACKAGE_NAME],
            # serial="emulator-5554",   # specify the serial
            maxStep=50,
            profile_period=10,
            take_screenshots=True,  # whether to take screenshots, default is False
            # running_mins=10,  # specify the maximal running time in minutes, default value is 10m
            # throttle=200,   # specify the throttle in milliseconds, default value is 200ms
            agent="u2"  # 'native' for running the vanilla Fastbot, 'u2' for running Kea2
        )
    )
    unittest.main(testRunner=KeaTestRunner)
