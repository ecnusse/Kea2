import unittest
import random
import uiautomator2 as u2
from uuid import uuid4
from kea2 import precondition, prob, max_tries

from kea2 import state   # stateful testing
state["notes"] = list()

def get_random_text():
    return uuid4().hex[:6]

class TestOmniNotes(unittest.TestCase):
    d: u2.Device

    @classmethod
    def setUpClass(cls):
        """Global setting for uiautomator2 (Optional)"""
        cls.d.settings["wait_timeout"] = 5.0
        cls.d.settings["operation_delay"] = (0, 1.0)
        cls.d.app_clear("it.feio.android.omninotes.alpha")

    @prob(0.3)
    @precondition(
        lambda self: self.d(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").exists
        and not self.d(resourceId="it.feio.android.omninotes.alpha:id/fab_note").exists
        and not self.d(resourceId="it.feio.android.omninotes.alpha:id/navdrawer_title").exists
    )
    def add_note(self):
        """stateful testing: add a note and store in state"""
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
        """stateful testing: search an existed note."""
        expected_note = random.choice(state["notes"])
        self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_search").click()
        self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").set_text(expected_note)
        self.d.press("enter")
        assert self.d(text=expected_note).exists, "the added note not found"
   
    @prob(0.7)
    @precondition(lambda self: self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists)
    def rotation_should_not_close_the_search_input(self):
        """Rotation should not close the search input.
        This property's assertion is expected to fail, demonstrating Kea2's ability to detect functional bugs."""
        self.d.set_orientation("l")
        self.d.set_orientation("n")
        assert self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists

    @precondition(lambda self: "camera" in self.d.app_current().get("package", ""))
    def exit_camera(self):
        """Guided exploration: Exit camera if it is launched 
        (fastbot can't exit camera app by itself, we use kea2 to exit it to avoid getting stuck in camera)"""
        print("Exiting camera app")
        pkg_camera = self.d.app_current().get("package", "")
        print(f"Current package: {pkg_camera}")
        if "camera" in pkg_camera:
            self.d.app_stop(pkg_camera)
    
    @max_tries(1)
    @precondition(lambda self: self.d(resourceId="it.feio.android.omninotes.alpha:id/next").exists)
    def skip_welcome_tour(self):
        """Guided exploration: skip welcome tour if it is shown.
        This is a one-shot action to skip the welcome tour (@max_tries(1))"""
        while self.d(resourceId="it.feio.android.omninotes.alpha:id/next").exists:
            self.d(resourceId="it.feio.android.omninotes.alpha:id/next").click()
        if self.d(resourceId="it.feio.android.omninotes.alpha:id/done").exists:
            self.d(resourceId="it.feio.android.omninotes.alpha:id/done").click()