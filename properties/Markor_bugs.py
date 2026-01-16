from kea2 import precondition,max_tries,prob
from kea2.state import state
from time import sleep
import unittest
import uiautomator2 as u2
import re
import random
import string

state['quicknote'] = None


class AnkiDroid_Propertytest_Sample(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect()

    @max_tries(1)
    @precondition(
        lambda self: self.d(resourceId='net.gsantner.markor:id/nav_quicknote',selected = True).exists
    )
    def test_add_quicknote(self):
        content = ''.join(random.choices("abc123XYZ", k=8))
        self.d(resourceId='net.gsantner.markor:id/document__fragment__edit__highlighting_editor').set_text(content)
        sleep(0.5)
        self.d(resourceId="net.gsantner.markor:id/action_save").click()
        state['quicknote'] = content
        print(state['quicknote'])

    @prob(0.6)
    @precondition(
        lambda self: self.d(resourceId='net.gsantner.markor:id/opoc_filesystem_item__title',text = 'QuickNote.md').exists
    )
    def test_delete_quicknote(self):
        self.d(resourceId='net.gsantner.markor:id/opoc_filesystem_item__title',text = 'QuickNote.md').long_click()
        sleep(0.5)
        self.d(resourceId='net.gsantner.markor:id/action_delete_selected_items').click()
        sleep(0.5)
        self.d(text='OK').click()
        sleep(0.5)
        state['quicknote'] = None
        print(state['quicknote'])
        assert not self.d(resourceId='net.gsantner.markor:id/opoc_filesystem_item__title',text = 'QuickNote.md').exists

    @prob(0.8)
    @precondition(
        lambda self: self.d(resourceId='net.gsantner.markor:id/nav_quicknote',selected = True).exists
    )
    def test_search_quicknote(self):
        content = self.d(resourceId='net.gsantner.markor:id/document__fragment__edit__highlighting_editor').get_text()
        print(f"Found quicknote content: {content}")
        print(f"Found content in state: {state['quicknote']}")
        assert state['quicknote'] == content


    @max_tries(1)
    @precondition(
        lambda self: self.d(resourceId='net.gsantner.markor:id/opoc_filesystem_item__title', text='QuickNote.md').exists
    )
    def test_update_quicknote(self):
        self.d(resourceId='net.gsantner.markor:id/opoc_filesystem_item__title', text='QuickNote.md').click()
        sleep(0.5)
        content = ''.join(random.choices("abc123XYZ", k=8))
        self.d(resourceId='net.gsantner.markor:id/document__fragment__edit__highlighting_editor').set_text(content)
        sleep(0.5)
        self.d(resourceId="net.gsantner.markor:id/action_save").click()
        state['quicknote'] = content
        sleep(0.5)
        self.d.press("back")
        sleep(0.5)
        self.d.press("back")
        sleep(0.5)
        print(state['quicknote'])
        assert self.d(resourceId='net.gsantner.markor:id/opoc_filesystem_item__title', text='QuickNote.md').exists



