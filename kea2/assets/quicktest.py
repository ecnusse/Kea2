import unittest
import uiautomator2 as u2

from time import sleep
from kea2 import precondition, prob, KeaTestRunner, Options, keaTestLoader, invariant


import unittest
import random
import uiautomator2 as u2
from uuid import uuid4
from kea2 import precondition, prob, max_tries

from kea2 import state   # stateful testing


URL = "https://github.com/federicoiosue/Omni-Notes/releases/download/6.2.0_alpha/OmniNotes-alphaRelease-6.2.0.apk"
FALL_BACK_URL = "https://gitee.com/XixianLiang/Kea2/raw/main/omninotes.apk"
PACKAGE_NAME = "it.feio.android.omninotes.alpha"
FILE_NAME = "omninotes.apk"


state["notes"] = list()

def get_random_text():
    return uuid4().hex[:6]

class TestOmniNotes(unittest.TestCase):
    d: u2.Device

    @classmethod
    def setUpClass(cls):
        """Global setting for uiautomator2 (Optional)
        """
        cls.d.settings["wait_timeout"] = 5.0
        cls.d.settings["operation_delay"] = (0, 1.0)
        cls.d.app_clear(PACKAGE_NAME)

    @prob(0.3)
    @precondition(
        lambda self: self.d(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").exists
        and not self.d(resourceId="it.feio.android.omninotes.alpha:id/fab_note").exists
        and not self.d(resourceId="it.feio.android.omninotes.alpha:id/navdrawer_title").exists
    )
    def add_note(self):
        """stateful testing: add a note and store in state
        """
        self.d(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").long_click()
        title = get_random_text()
        self.d(resourceId="it.feio.android.omninotes.alpha:id/detail_title").set_text(title)
        self.d(description="drawer open").click()
        state["notes"].append(title)

    @prob(0.3)
    @precondition(
        lambda self: self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_search").exists 
        and len(state["notes"]) > 0
        and not self.d(resourceId="it.feio.android.omninotes.alpha:id/navdrawer_title").exists
    )
    def search_note(self):
        """stateful testing: search an existed note.
        """
        expected_note = random.choice(state["notes"])
        self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_search").click()
        self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").set_text(expected_note)
        self.d.press("enter")
        assert self.d(text=expected_note).exists, "the added note not found"
    
    @precondition(lambda self: "camera" in self.d.app_current().get("package", ""))
    def exit_camera(self):
        """Guided exploration: Exit camera if it is launched 
        (fastbot can't exit camera app by itself, we use kea2 to exit it to avoid getting stuck in camera)
        """
        print("Exiting camera app")
        pkg_camera = self.d.app_current().get("package", "")
        print(f"Current package: {pkg_camera}")
        if "camera" in pkg_camera:
            self.d.app_stop(pkg_camera)
    
    @max_tries(1)
    @precondition(lambda self: self.d(resourceId="it.feio.android.omninotes.alpha:id/next").exists)
    def skip_welcome_tour(self):
        """Guided exploration: skip welcome tour if it is shown.
        This is a one-shot action to skip the welcome tour (@max_tries(1))
        """
        while self.d(resourceId="it.feio.android.omninotes.alpha:id/next").exists:
            self.d(resourceId="it.feio.android.omninotes.alpha:id/next").click()
        if self.d(resourceId="it.feio.android.omninotes.alpha:id/done").exists:
            self.d(resourceId="it.feio.android.omninotes.alpha:id/done").click()
            
    @invariant
    def search_button_and_search_input_box_should_not_exists_at_the_same_time(self):
        """Search input box and search button should not exists at the same time
        """
        search_input_box_exists = self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists
        serach_button_exists = self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_search").exists
        if search_input_box_exists or serach_button_exists:
            assert search_input_box_exists ^ serach_button_exists
            


# Download Utils
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
    unittest.main(testRunner=KeaTestRunner, testLoader=keaTestLoader)
