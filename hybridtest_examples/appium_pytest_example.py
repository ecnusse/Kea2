import os
import pytest
from time import sleep
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from kea2 import Kea2Tester, Options
from appium.options.android import UiAutomator2Options

PACKAGE_NAME = "it.feio.android.omninotes.alpha"
DEVICE_SERIAL = "emulator-5554"
APPIUM_SERVER_URL = "http://localhost:4723"


class TestFeat4Example1:
    def setup_method(self):
        """Test pre-operation: Connect device and restart application"""
        print("\n" + "="*60)
        print("setup_method: Connect device and restart application")
        print("="*60)
        
        self.desired_caps = {
            "platformName": "Android",
            "deviceName": "Android Device",
            "uid": DEVICE_SERIAL,
            "appPackage": PACKAGE_NAME,
            "appActivity": "it.feio.android.omninotes.MainActivity",
            "automationName": "UiAutomator2",
            "noReset": True,  # Do not reset app state on each launch
            "fullReset": False,
            "unicodeKeyboard": True,
            "resetKeyboard": True
        }
        self.option = UiAutomator2Options().load_capabilities(self.desired_caps)
        self.driver = webdriver.Remote(
            APPIUM_SERVER_URL, 
            options=self.option
        )
        self.driver.implicitly_wait(10)
        self.driver.terminate_app(PACKAGE_NAME)
        self.driver.activate_app(PACKAGE_NAME)

        sleep(2)

    def test_case1_add_tag_show_tags(self):
        '''add note -> add tag -> show tags'''
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/fab_expand_menu_button"
        ).click()
        add_note_btn = self.driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/fab_note"
        )
        add_note_btn.click()
        sleep(1)

        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/detail_content"
        ).send_keys("hello kea2! #hello")
        
        self.driver.find_element(
            AppiumBy.ACCESSIBILITY_ID, "More options"
        ).click()
        
        try:
            self.driver.find_element(
                AppiumBy.XPATH, "//android.widget.TextView[@text='Disable checklist']"
            ).click()
        except:
            self.driver.back()
        
        # Check the KEA2_HYBRID_MODE environment variable
        if os.environ.get('KEA2_HYBRID_MODE', '').lower() == 'true':    
            print("close Appium session")
            self.driver.quit()
            
            # launch Kea2 test
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
            del tester
            return
        
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/menu_tag"
        ).click()
    
    def test_case2_add_category(self):
        '''add note -> add category -> start kea2 testing'''
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/fab_expand_menu_button"
        ).click()
        sleep(1)
        
        add_note_btn = self.driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/fab_note"
        )
        add_note_btn.click()
        sleep(1)

        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/detail_content"
        ).send_keys("Hello world")
        sleep(2)
        
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/menu_category"
        ).click()
        sleep(0.5)
        
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/md_buttonDefaultPositive"
        ).click()
        sleep(0.5)
        
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/category_title"
        ).send_keys("aaa")
        sleep(1)
        
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/save"
        ).click()
        
        # Check the KEA2_HYBRID_MODE environment variable
        if os.environ.get('KEA2_HYBRID_MODE', '').lower() == 'true':    
            print("close Appium session")
            self.driver.quit()
            
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
            del tester
            return
        
        print("This part will not execute when KEA2_HYBRID_MODE is kea2")
    
    def test_case3_delete_note_search(self):
        '''add note -> delete note -> search title'''
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/fab_expand_menu_button"
        ).click()
        

        add_note_btn = self.driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/fab_note"
        )
        add_note_btn.click()
        sleep(1)
        

        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/detail_title"
        ).send_keys("Hello112233")
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/detail_content"
        ).send_keys("Hello world")
        
        self.driver.find_element(
            AppiumBy.ACCESSIBILITY_ID, "drawer open"
        ).click()
        
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/note_title"
        ).click()
        
        self.driver.find_element(
            AppiumBy.ACCESSIBILITY_ID, "More options"
        ).click()
        self.driver.find_element(
            AppiumBy.XPATH, "//android.widget.TextView[@text='Trash']"
        ).click()
        
        # Check the KEA2_HYBRID_MODE environment variable
        if os.environ.get('KEA2_HYBRID_MODE', '').lower() == "true":
            print("close Appium session")
            self.driver.quit()
            
            # launch Kea2 testing
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
            del tester
            return
        
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/menu_search"
        ).click()
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/search_src_text"
        ).send_keys("Hello112233")
        self.driver.press_keycode(66)
    
    def teardown_method(self):
        """Test post-operation: Cleanup work"""
        print("\n" + "="*60)
        print("teardown_method: Cleanup work")
        print("="*60)
        # self.driver.quit()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
