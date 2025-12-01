from kea2 import precondition,prob,max_tries
from time import sleep
import unittest
import uiautomator2 as u2


class Omni_Notes_Propertytest_Sample(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect()

    @prob(0.7)  # The probability of executing the function when precondition is satisfied.
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

    @max_tries(1)
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
        self.d.set_orientation("l")
        sleep(2)
        self.d.set_orientation("n")
        sleep(2)
        assert self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists()
