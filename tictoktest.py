import unittest
import uiautomator2 as u2

from time import sleep
from kea2 import precondition, prob, KeaTestRunner, Options, max_tries
from kea2.u2Driver import U2Driver


class Omni_Notes_Sample(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect() 
    
    #page1:message
    @max_tries(1)
    @precondition(
        lambda self: self.d(text="聊天").exists
    )
    def test_messagepage(self):
        print("message page get")
        sleep(0.5)
    
    #page2:comments
    @max_tries(1)
    @precondition(
        lambda self: self.d(text="回复").exists
    )
    def test_commentspage(self):
        print("comment page get")
        sleep(0.5)

    #page3:margin
    @max_tries(1)
    @precondition(
        lambda self: self.d(text="我的钱包").exists
    )
    def test_marginpage(self):
        print("margin page get")
        sleep(0.5)

    #page4:history
    @max_tries(1)
    @precondition(
        lambda self: self.d(text="观看历史").exists
        and self.d(text="影视综").exists
    )
    def test_historypage(self):
        print("history page get")
        sleep(0.5)

    #page5:settings
    @max_tries(1)
    @precondition(
        lambda self: self.d(text="设置").exists
        and self.d(text="账号与安全").exists
    )
    def test_settingspage(self):
        print("settings page get")
        sleep(0.5)

    #page6:about
    @max_tries(1)
    @precondition(
        lambda self: self.d(text="访问抖音官网").exists
    )
    def test_aboutpage(self):
        print("about page get")
        sleep(0.5)

    #page7:check bgm
    @max_tries(1)
    @precondition(
        lambda self: self.d(text="拍同款").exists
        and self.d(text="去听完整版").exists
    )
    def test_checkbgmpage(self):
        print("bgm page get")
        sleep(0.5)

    @max_tries(1)
    #page8:SEARCH PAGE
    @precondition(
        lambda self: self.d(text="搜").exists
    )
    def test_searchpage(self):
        print("search page get")
        sleep(0.5)   

    @max_tries(1)
    #page9:filmpage
    @precondition(
        lambda self: self.d(text="闪光灯").exists
    )
    def test_filmpage(self):
        print("film page get")
        sleep(0.5)

    @max_tries(1)
    #page10:tool page
    @precondition(
        lambda self: self.d(text="我的功能").exists
    )
    def test_toolpage(self):
        print("tool page get")
        sleep(0.5)                       

PACKAGE_NAME = "com.ss.android.ugc.aweme"
FILE_NAME = "omninotes.apk"


def check_installation(serial=None):
    import os
    from pathlib import Path
    
    d = u2.connect(serial)
    # automatically install omni-notes
    if PACKAGE_NAME not in d.app_list():
        if not os.path.exists(Path(".") / FILE_NAME):
            print(f"[INFO] omninote.apk not exists.", flush=True)
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
            running_mins=60,
            profile_period=10,
            take_screenshots=True,  # whether to take screenshots, default is False
            # running_mins=10,  # specify the maximal running time in minutes, default value is 10m
            # throttle=200,   # specify the throttle in milliseconds, default value is 200ms
            agent="u2",  # 'native' for running the vanilla Fastbot, 'u2' for running Kea2
        )
    )
    unittest.main(testRunner=KeaTestRunner)
