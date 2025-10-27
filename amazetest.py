import unittest
import uiautomator2 as u2

from time import sleep
from kea2 import precondition, prob, KeaTestRunner, Options
from kea2.keaUtils import max_tries
from kea2.u2Driver import U2Driver
import random
import string


class Amaze_Test(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect()

    @precondition(
        lambda self: self.d(text="Documents").exists and 
        self.d(resourceId="com.amaze.filemanager:id/firstline").exists
    )
    @prob(0.8)
    @max_tries(1)
    def test_delete_document(self):
        pre_count = self.d(resourceId="com.amaze.filemanager:id/firstline").count
        obj = self.d(resourceId="com.amaze.filemanager:id/properties")[0]
        obj.click()
        self.d(text="Delete").click()
        self.d(text="DELETE").click()
        cur_count = self.d(resourceId="com.amaze.filemanager:id/firstline").count
        assert cur_count == pre_count - 1

    @precondition(
        lambda self: self.d(text="Sort").exists and
        self.d(text="/storage/emulated/0").exists
    )
    @prob(0.8)
    @max_tries(1)
    def test_sort(self):
        self.d(text="Sort").click()
        self.d(text="Sort By").click()
        self.d(text="ASCENDING").click()
        assert self.d(text="amap").exists()

    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/sd_main_fab").exists and 
        self.d(text="/storage/emulated/0/Music").exists
    )
    @prob(0.8)
    @max_tries(1)
    def test_create_folder(self):
        alphabet = string.ascii_letters + string.digits
        str = ''.join(random.choices(alphabet, k=8))
        self.d(resourceId="com.amaze.filemanager:id/sd_main_fab").click()
        self.d(text="Folder").click()
        self.d(text="Enter Name").set_text(str)
        self.d(text="CREATE").click()
        assert self.d(text=str).exists()

    @precondition(
        lambda self: self.d(text="Movies").exists and 
        self.d(text="Download").exists
    )
    @prob(0.8)
    @max_tries(1)
    def test_edit_folder_name(self):
        self.d(resourceId="com.amaze.filemanager:id/design_menu_item_action_area")[1].click()
        self.d(resourceId="com.amaze.filemanager:id/editText4").click()
        self.d(resourceId="com.amaze.filemanager:id/editText4").set_text("")
        self.d(resourceId="com.amaze.filemanager:id/editText4").set_text("hello")
        self.d(text="SAVE").click()
        assert self.d(text="hello").exists()
    
    @precondition(
        lambda self: self.d(text="Images").exists and 
        self.d(resourceId="com.amaze.filemanager:id/firstline").exists
    )
    @prob(0.8)
    @max_tries(1)
    def test_edit_image_name(self):
        self.d(resourceId="com.amaze.filemanager:id/properties")[0].click()
        self.d(text="Rename").click()
        self.d(resourceId="com.amaze.filemanager:id/singleedittext_input").set_text("")
        self.d(resourceId="com.amaze.filemanager:id/singleedittext_input").set_text("Screenshot1.jpg")
        self.d(text="SAVE").click()
        assert self.d(text="Screenshot1.jpg").exists()
    
    @precondition(
        lambda self: self.d(text="Audio").exists and 
        self.d(resourceId="com.amaze.filemanager:id/firstline").exists
    )
    @prob(0.8)
    @max_tries(1)
    def test_delete_audio(self):
        pre_count = self.d(resourceId="com.amaze.filemanager:id/firstline").count
        self.d(resourceId="com.amaze.filemanager:id/firstline")[0].long_click()
        self.d(resourceId="com.amaze.filemanager:id/search").click()
        self.d(text="DELETE").click()
        cur_count = self.d(resourceId="com.amaze.filemanager:id/firstline").count
        assert cur_count == pre_count - 1

    @precondition(
        lambda self: self.d(text="APKs").exists and 
        self.d(resourceId="com.amaze.filemanager:id/firstline").exists
    )
    @prob(0.8)
    @max_tries(1)
    def test_share_apks(self):
        self.d(resourceId="com.amaze.filemanager:id/properties")[0].click()
        self.d(text="Share").click()
        assert self.d(text="Bluetooth").exists() and self.d(text="Email").exists()
    
    @precondition(
        lambda self: self.d(text="Recent files").exists and 
        self.d(resourceId="com.amaze.filemanager:id/firstline").exists
    )
    @prob(0.8)
    @max_tries(1)
    def test_recent_return_home(self):
        self.d(resourceId="com.amaze.filemanager:id/home").click()
        assert self.d(text="/storage/emulated/0").exists()