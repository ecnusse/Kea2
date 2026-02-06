import pytest
import uiautomator2 as u2
from time import sleep
from kea2 import Kea2Tester, Options
import os


PACKAGE_NAME = "it.feio.android.omninotes.alpha"
DEVICE_SERIAL = "emulator-5554"


@pytest.fixture(scope="function")
def setup_and_teardown():
    print("\n" + "="*60)
    print("setup: Connect device and restart application")
    print("="*60)
    
    d = u2.connect(DEVICE_SERIAL)
    d.app_stop(PACKAGE_NAME)
    d.app_start(PACKAGE_NAME)
    sleep(2)
    
    yield d
    
    print("\n" + "="*60)
    print("teardown: Cleanup work")
    print("="*60)


def test_case1_add_tag_show_tags(setup_and_teardown):
    """add note -> add tag -> show tags"""
    d = setup_and_teardown
    
    d(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").long_click()
    d(resourceId="it.feio.android.omninotes.alpha:id/detail_content").set_text("hello kea2! #hello")
    d(description="More options").click()
    
    if d(text="Disable checklist").exists():
        d(text="Disable checklist").click()
    else:
        d.press("back")

    # Check the KEA2_HYBRID_MODE environment variable
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

        return

    d(resourceId="it.feio.android.omninotes.alpha:id/menu_tag").click()


def test_case2_add_category(setup_and_teardown):
    """add note -> add category -> start kea2 testing"""
    d = setup_and_teardown
    
    d(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").long_click()
    sleep(1)
    d(resourceId="it.feio.android.omninotes.alpha:id/detail_content").set_text("Hello world")
    sleep(2)
    d(resourceId="it.feio.android.omninotes.alpha:id/menu_category").click()
    sleep(0.5)
    d(resourceId="it.feio.android.omninotes.alpha:id/md_buttonDefaultPositive").click()
    sleep(0.5)
    d(resourceId="it.feio.android.omninotes.alpha:id/category_title").set_text("aaa")
    d(resourceId="it.feio.android.omninotes.alpha:id/save").click()        

    # Check the KEA2_HYBRID_MODE environment variable
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

        return
    
    print("This part will not execute when KEA2_HYBRID_MODE is true")


def test_case3_delete_note_search(setup_and_teardown):
    """add note -> delete note -> search title"""
    d = setup_and_teardown
    
    d(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").long_click()
    d(resourceId="it.feio.android.omninotes.alpha:id/detail_title").set_text("Hello112233")
    d(resourceId="it.feio.android.omninotes.alpha:id/detail_content").set_text("Hello world")
    d(description="drawer open").click()
    d(resourceId="it.feio.android.omninotes.alpha:id/note_title").long_click()
    d(description="More options").click()
    d(text="Trash").click()

    # Check the KEA2_HYBRID_MODE environment variable
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
        return

    d(resourceId="it.feio.android.omninotes.alpha:id/menu_search").click()
    d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").set_text("Hello112233")
    d.press("enter")
