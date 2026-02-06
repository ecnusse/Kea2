import unittest
import uiautomator2 as u2
from time import sleep
from kea2 import Kea2Tester, Options
import os


PACKAGE_NAME = "it.feio.android.omninotes.alpha"
DEVICE_SERIAL = "emulator-5554"


class Feat4_Example1(unittest.TestCase):    
    
    def setUp(self):
        print("\n" + "="*60)
        print("setUp: Connect device and restart application")
        print("="*60)
        self.d = u2.connect(DEVICE_SERIAL)
        self.d.app_stop(PACKAGE_NAME)
        self.d.app_start(PACKAGE_NAME)
        sleep(2)
    
    def test_case1_add_tag_show_tags(self):
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
        
        if os.environ.get('KEA2_HYBRID_MODE', '').lower() == 'true':

            tester = Kea2Tester()
            result = tester.run_kea2_testing(
                Options(
                    driverName="d",
                    packageNames=[PACKAGE_NAME],
                    propertytest_args=["discover", "-p", "Omninotes_Sample.py"],
                    serial=DEVICE_SERIAL,
                    running_mins=2,
                    maxStep=20
                )        
            )
            print(result)

            return  #Subsequent code will not execute

        self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_tag").click()

    
    def test_case2_add_category(self):
        '''
        add note -> add category -> start kea2 testing
        '''

        self.d(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").long_click()
        sleep(1)
        self.d(resourceId="it.feio.android.omninotes.alpha:id/detail_content").set_text("Hello world")
        sleep(2)
        self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_category").click()
        sleep(0.5)
        self.d(resourceId="it.feio.android.omninotes.alpha:id/md_buttonDefaultPositive").click()
        sleep(0.5)
        self.d(resourceId="it.feio.android.omninotes.alpha:id/category_title").set_text("aaa")
        self.d(resourceId="it.feio.android.omninotes.alpha:id/save").click()        

        if os.environ.get('KEA2_HYBRID_MODE', '').lower() == 'true':

            tester = Kea2Tester()
            result = tester.run_kea2_testing(
                Options(
                    driverName="d",
                    packageNames=[PACKAGE_NAME],
                    propertytest_args=["discover", "-p", "Omninotes_Sample.py"],
                    serial=DEVICE_SERIAL,
                    running_mins=2,
                    maxStep=20
                )
            )
            print(result)
            return  #Subsequent code will not execute
        
        print("This part will not execute when KEA2_HYBRID_MODE is true")


    def test_case3_delete_note_search(self):
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

        if os.environ.get('KEA2_HYBRID_MODE', '').lower() == 'true':
            tester = Kea2Tester()
            result = tester.run_kea2_testing(
                Options(
                    driverName="d",
                    packageNames=[PACKAGE_NAME],
                    propertytest_args=["discover", "-p", "Omninotes_Sample.py"],
                    serial=DEVICE_SERIAL,
                    running_mins=2,
                    maxStep=20
                )
            )
            print(result)

            return  #Subsequent code will not execute

        self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_search").click()
        self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").set_text("Hello112233")
        self.d.press("enter")


    def tearDown(self):
        """Cleanup work after testing"""
        print("\n" + "="*60)
        print("\ntearDown: Cleanup work")
        print("="*60)


def main():
    unittest.main(verbosity=2)

if __name__ == "__main__":
    main()
