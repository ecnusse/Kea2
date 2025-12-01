import unittest
import uiautomator2 as u2
from time import sleep
from kea2 import interruptable, kea2_breakpoint

class Omni_Notes_Unittest_Sample(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect()

    def test_unittest_rotation(self):
        self.d.set_orientation('l')
        sleep(1)
        self.d.set_orientation('n')
        sleep(1)
        self.d.set_orientation('r')
        sleep(1)
        self.d.set_orientation('n')
        sleep(1)

    @interruptable()
    def test_unittest_add_note_add_category(self):
        '''
        add note -> add category
        '''
        self.d(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").long_click()
        sleep(1)
        self.d(resourceId="it.feio.android.omninotes.alpha:id/detail_content").set_text("Hello world")
        sleep(2)
        self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_category").click()
        sleep(0.5)
        kea2_breakpoint()
        self.d(resourceId="it.feio.android.omninotes.alpha:id/md_buttonDefaultPositive").click()
        sleep(0.5)
        self.d(resourceId="it.feio.android.omninotes.alpha:id/category_title").set_text("aaa")
        self.d(resourceId="it.feio.android.omninotes.alpha:id/save").click()

    
    @interruptable()
    def test_unittest_delete_note_search(self):
        '''
        add note -> delete note -> search title
        '''
        self.d(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").long_click()
        self.d(resourceId="it.feio.android.omninotes.alpha:id/detail_title").set_text("Hello112233")
        self.d(resourceId="it.feio.android.omninotes.alpha:id/detail_content").set_text("Hello world")
        self.d(description="drawer open").click()
        self.d(resourceId="it.feio.android.omninotes.alpha:id/note_title").long_click()
        self.d(description="More options").click()
        self.d(text="Trash").click()

        self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_search").click()
        self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").set_text("Hello112233")
        self.d.press("enter")


    @interruptable()
    def test_unitttest_add_tag_show_tags(self):
        '''
        add note -> add tag -> show tags
        '''
        self.d(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").long_click()
        self.d(resourceId="it.feio.android.omninotes.alpha:id/detail_content").set_text("hello kea2! #hello")
        self.d(description = "More options").click()
        
        if self.d(text="Disable checklist").exists():
            self.d(text="Disable checklist").click()
        else:
            self.d.press("back")
        
        self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_tag").click()

    def tearDown(self):
        print("================default teardown=============")



