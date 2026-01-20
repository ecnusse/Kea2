import secrets
import unittest
import uiautomator2 as u2

from time import sleep
from kea2 import precondition, prob, KeaTestRunner, Options
from kea2.keaUtils import max_tries
from kea2 import invariant
from typing import List
import random
import string
import re


class Amaze_Test(unittest.TestCase):

    d: u2.Device
    
    @classmethod
    def setUpClass(cls):
        cls.d.settings['wait_timeout'] = 5.0
        cls.d.settings["operation_delay"] = (0, 1.0)
    
    def rand_alnum(self, n: int) -> str:
        alphabet = string.ascii_letters + string.digits  # a-zA-Z0-9
        return ''.join(secrets.choice(alphabet) for _ in range(n))
    
    def get_available_items(self) -> List[u2.UiObject]:
        if not self.d(resourceId="com.amaze.filemanager:id/second").exists:
            return list()
        items: List[u2.UiObject] = list(self.d(resourceId="com.amaze.filemanager:id/second"))
        filtered_items: List[u2.UiObject] = []
        for item in items:
            if not item.child(resourceId="com.amaze.filemanager:id/properties").exists:
                continue
            filtered_items.append(item)
        return filtered_items

    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/second").exists
    )
    @prob(0.3)
    def test_delete_folders(self):
        filtered_items = self.get_available_items()
        t = random.choice(filtered_items)
        title = t.child(resourceId="com.amaze.filemanager:id/firstline").get_text()
        target = t.child(resourceId="com.amaze.filemanager:id/properties")

        print(f"Trying to click {title}")
        target.click()

        self.d(text="Delete").click()
        self.d(text="DELETE").click()
        assert not self.d(text=title).exists

    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/sd_main_fab").exists
    )
    @prob(0.3)
    def test_create_folder(self):
        random_text = self.rand_alnum(6)
        self.d(resourceId="com.amaze.filemanager:id/sd_main_fab").click()
        self.d(text="Folder").click()
        self.d(text="Enter Name").set_text(random_text)
        self.d(text="CREATE").click()
        assert self.d(text=random_text).exists()

    @precondition(
        lambda self: self.d(text="Images").exists and 
        self.d(text="Documents").exists
    )
    @prob(0.3)
    def test_edit_menu_name(self):
        num = random.randint(2, 4)
        random_text = self.rand_alnum(6)
        self.d(resourceId="com.amaze.filemanager:id/design_menu_item_action_area")[num].click()
        self.d(resourceId="com.amaze.filemanager:id/editText4").click()
        self.d(resourceId="com.amaze.filemanager:id/editText4").set_text("")
        self.d(resourceId="com.amaze.filemanager:id/editText4").set_text(random_text)
        self.d(text="SAVE").click()
        assert self.d(text=random_text).exists()
    
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/second").exists
    )
    @prob(0.3)
    def test_edit_folder_name(self):
        filtered_items = self.get_available_items()
        
        t = random.choice(filtered_items)
        title = t.child(resourceId="com.amaze.filemanager:id/firstline").get_text()
        target = t.child(resourceId="com.amaze.filemanager:id/properties")

        print(f"Trying to click {title}")
        target.click()

        random_text = self.rand_alnum(6)

        self.d(text="Rename").click()
        self.d(resourceId="com.amaze.filemanager:id/singleedittext_input").set_text("")
        self.d(resourceId="com.amaze.filemanager:id/singleedittext_input").set_text(random_text)
        self.d(text="SAVE").click()
        assert self.d(text=random_text).exists

    @precondition(
        lambda self: self.d(text="Share").exists
    )
    @prob(0.3)
    def test_share(self):
        self.d(text="Share").click()
        assert self.d(text="Bluetooth").exists() and self.d(text="Email").exists()
    
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/home").exists
    )
    @prob(0.1)
    def test_recent_return_home(self):
        self.d(resourceId="com.amaze.filemanager:id/home").click()
        assert self.d(text="/storage/emulated/0").exists()

    @prob(0.1)
    @precondition(
        lambda self: self.d(description="More options").exists
    )
    def test_exit(self):
        self.d(description="More options").click()
        self.d(text="Exit").click()

        assert "launcher" in self.d.app_current()["package"], "App did not exit to launcher"

    @prob(0.2)
    @precondition(lambda self: self.d(resourceId="com.amaze.filemanager:id/action_mode_close_button").exists)
    def select_count_exists_when_selecting_multiple_files(self):
        """
        Selecting multiple files should show the correct count in the action bar.
        """
        item_count = int(self.d(resourceId="com.amaze.filemanager:id/item_count").get_text())
        assert item_count > 0, "Item count should be greater than 0 when files are selected."

        # e.g.:   "118 folders and 28 files"
        total_file_info = re.compile(r"(\d+)\s+folders?\s+and\s+(\d+)\s+files?")
        actual_file_info = self.d(resourceId="com.amaze.filemanager:id/pathname").get_text()
        assert total_file_info.match(actual_file_info), f"File info format is incorrect: {actual_file_info}"

    @prob(0.2)
    @precondition(lambda self: self.d(resourceId="com.amaze.filemanager:id/item_count").exists)
    def select_all_should_work(self):
        total_file_info = re.compile(r"(\d+)\s+folders?\s+and\s+(\d+)\s+files?")
        actual_file_info = self.d(resourceId="com.amaze.filemanager:id/pathname").get_text()
        match = total_file_info.match(actual_file_info)
        folder_count = int(match.group(1))
        file_count = int(match.group(2))
        total_file_info = folder_count + file_count
        item_count = int(self.d(resourceId="com.amaze.filemanager:id/item_count").get_text())
        self.d(resourceId="com.amaze.filemanager:id/item_count").sibling(className="android.widget.ImageView").click()
        self.d(text="Select All").click()
        assert item_count == total_file_info, f"Select All did not select all items: {item_count} != {total_file_info}"

    @prob(0.2)
    @precondition(lambda self: self.d(text="Deselect All").exists)
    def unselect_all_should_work(self):
        self.d(text="Deselect All").click()
        assert not self.d(resourceId="com.amaze.filemanager:id/action_mode_close_button").exists, "Deselect All did not clear selection."

    @invariant
    def select_count_should_match_selected_items(self):
        """
        The count of selected items should match the actual number of selected items.
        """
        if self.d(resourceId="com.amaze.filemanager:id/check_icon").exists:
            item_count = int(self.d(resourceId="com.amaze.filemanager:id/item_count").get_text())
            assert len(self.d(resourceId="com.amaze.filemanager:id/check_icon")) == item_count, "Selected item count does not match actual selected items."

    @prob(0.1)
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/fullpath").exists
    )
    def current_path_shuold_display_in_history(self):
        current_path = self.d(resourceId="com.amaze.filemanager:id/fullpath").get_text()
        self.d(description="More options").click()
        self.d(text="History").click()
        full_paths = list(self.d(resourceId="com.amaze.filemanager:id/file_path"))
        first_path = full_paths[0].get_text()
        assert first_path == current_path, f"Current path {current_path} does not match history path {first_path}"

    # 新建云链接    
    @prob(0.1)
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/sd_main_fab").exists
    )
    def test_add_cloud_connection(self):
        self.d(resourceId="com.amaze.filemanager:id/sd_main_fab").click()
        self.d(text="Cloud Connection").click()
        assert not self.d(text="SMB Connection").exists and self.d(text="SCP/SFTP Connection").exists

    # 长按复制文件
    @prob(0.1)
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/second").exists
    )
    def test_long_click_copy(self):
        filtered_items = self.get_available_items()
        t = random.choice(filtered_items)
        t.long_click()
        self.d(resourceId="com.amaze.filemanager:id/cpy").click()
        self.d(text="PASTE").click()
        assert self.d(text="File with same name already exists").exists

    # 覆盖原文件    
    @prob(0.1)
    @precondition(
        lambda self: self.d(text="File with same name already exists").exists
    )
    def test_overwrite_is_enabled(self):
        assert self.d(text="SKIP").info["enabled"] == True and self.d(text="OVERWRITE").info["enabled"] == True and self.d(text="RENAME").info["enabled"] == True

    # 长按删除文件
    @prob(0.1)
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/second").exists
    )
    def test_long_click_delete(self):
        filtered_items = self.get_available_items()
        t = random.choice(filtered_items)
        t.long_click()
        title = t.child(resourceId="com.amaze.filemanager:id/firstline").get_text()
        self.d(resourceId="com.amaze.filemanager:id/delete").click()
        self.d(text="DELETE").click()
        assert not self.d(text=title).exists

    # 恢复文件
    @prob(0.1)
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/second").exists
        and self.d(text="Trash Bin").exists
    )
    def test_restore(self):
        filtered_items = self.get_available_items()
        t = random.choice(filtered_items)
        title = t.child(resourceId="com.amaze.filemanager:id/firstline").get_text()
        target = t.child(resourceId="com.amaze.filemanager:id/properties")
        target.click()
        self.d(text="Restore").click()
        self.d(text="DONE").click()
        assert not self.d(text=title).exists

    # 长按恢复文件
    @prob(0.1)
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/second").exists
        and self.d(text="Trash Bin").exists
    )
    def test_long_click_restore(self):
        filtered_items = self.get_available_items()
        t = random.choice(filtered_items)
        title = t.child(resourceId="com.amaze.filemanager:id/firstline").get_text()
        t.long_click()
        self.d(resourceId="com.amaze.filemanager:id/home").click()
        self.d(text="DONE").click()
        assert not self.d(text=title).exists

    @prob(0.1)
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/search").exists and
        not self.d(resourceId="com.amaze.filemanager:id/search_edit_text").exists
    )
    def search_file(self):
        items = self.get_available_items()
        if not items:
            raise unittest.SkipTest("No items available to search.")
        item = random.choice(items)
        title = item.child(resourceId="com.amaze.filemanager:id/firstline").get_text()
        search_letter = random.choice(title)
        self.d(resourceId="com.amaze.filemanager:id/search").click()
        self.d(resourceId="com.amaze.filemanager:id/search_edit_text").set_text(search_letter)
        self.d.press("enter")
        res_exist = self.d(resourceId="com.amaze.filemanager:id/searchRecyclerView").child_by_text(
            title, allow_scroll_search=True
        ).exists
        assert res_exist, f"Search for {search_letter} did not return expected item {title}."

    @prob(0.4)
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/search_edit_text").exists and
        self.d(resourceId="com.amaze.filemanager:id/searchResultsSortHintTV", text="Sort By:").exists
    )
    def sort_search_results(self):
        self.d(resourceId="com.amaze.filemanager:id/searchResultsSortButton").click()
        sort_bys: List[u2.UiObject] = list(self.d(resourceId="com.amaze.filemanager:id/md_control"))
        random.choice(sort_bys).click()
        self.d(text="ASCENDING").click()

        ascending_titles = list(self.d(resourceId="com.amaze.filemanager:id/searchItemFileNameTV"))
        assert ascending_titles, "No search results found after sorting ascending."

        ascending_titles = [title.get_text() for title in ascending_titles]

        self.d(resourceId="com.amaze.filemanager:id/searchResultsSortButton").click()
        self.d(text="DESCENDING").click()

        pivot_title = random.choice(ascending_titles)
        pivot_exists = self.d(resourceId="com.amaze.filemanager:id/searchRecyclerView").child_by_text(
            pivot_title, allow_scroll_search=True
        ).exists
        
        assert pivot_exists, f"Pivot title {pivot_title} not found after sorting descending."
        
        descending_titles = list(self.d(resourceId="com.amaze.filemanager:id/searchItemFileNameTV"))
        assert descending_titles, "No search results found after sorting descending."
        descending_titles = [title.get_text() for title in descending_titles]
        
        asc_set = set(ascending_titles)
        desc_set = set(descending_titles)
        common_asc = [title for title in ascending_titles if title in desc_set]
        common_desc = [title for title in descending_titles if title in asc_set]
        assert common_asc, "No overlapping titles between ascending and descending results."
        assert common_desc == list(reversed(common_asc)), (
            "Descending order is not the reverse of ascending order for common items."
        )
        
    @prob(0.4)
    @precondition(
        lambda self: self.d(resourceId="com.amaze.filemanager:id/search_edit_text").exists and
        self.d(resourceId="com.amaze.filemanager:id/searchResultsSortButton", text="Name").exists
    )
    def sort_by_name_should_work(self):
        titles = list(self.d(resourceId="com.amaze.filemanager:id/searchItemFileNameTV"))
        titles_texts = [title.get_text() for title in titles]
        sorted_titles = sorted(titles_texts)
        is_ascending = titles_texts == sorted_titles
        is_descending = titles_texts == list(reversed(sorted_titles))
        assert is_ascending or is_descending, "Search results are not sorted by name correctly"
    
if __name__ == "__main__":
    test_method = "test_delete_folders"

    Amaze_Test.d = u2.connect()
    t = Amaze_Test()
    t.setUpClass()
    for method in getattr(t, test_method).preconds:
        if not method(t):
            print(f"Precondition failed.")
            exit(1)
    getattr(t, test_method)()

    # Amaze_Test.d = u2.connect()
    # t = Amaze_Test()
    # t.select_count_should_match_selected_items()
