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
        """Global setting for uiautomator2 (Optional)
        """
        cls.d.settings["wait_timeout"] = 5.0
        cls.d.settings["operation_delay"] = (0, 1.0)
        cls.d.app_clear("it.feio.android.omninotes.alpha")

    @prob(0.7)
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
    
    @precondition(lambda self: self.d(resourceId="it.feio.android.omninotes.alpha:id/next").exists)
    def skip_welcome_tour(self):
        """Guided exploration: skip welcome tour if it is shown.
        This is a one-shot action to skip the welcome tour (@max_tries(1))
        """
        while self.d(resourceId="it.feio.android.omninotes.alpha:id/next").exists:
            self.d(resourceId="it.feio.android.omninotes.alpha:id/next").click()
        if self.d(resourceId="it.feio.android.omninotes.alpha:id/done").exists:
            self.d(resourceId="it.feio.android.omninotes.alpha:id/done").click()