from kea2 import precondition,max_tries
from kea2.state import state
from properties.ankiDroid_state_utils import ensure_card_types_default, add_card_type, last_card_type, pop_card_type, get_random_new_card_limit
from time import sleep
import unittest
import uiautomator2 as u2
import re
import random
import string

try:
    state['card_number'] = int(state.get('card_number', 0))
except Exception:
    state['card_number'] = 0

ensure_card_types_default()
state['tags'] = []

class AnkiDroid_Propertytest_Sample(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect()

    @max_tries(1)
    @precondition(
        lambda self: self.d(resourceId="com.ichi2.anki:id/DeckPickerHoriz").exists
    )
    def test_open_card_types(self):
        self.d(resourceId="com.ichi2.anki:id/DeckPickerHoriz").click()
        sleep(0.5)
        self.d(text='Add').click()
        sleep(0.5)
        self.d(resourceId="com.ichi2.anki:id/CardEditorCardsButton").click()

    @max_tries(1)
    @precondition(
        lambda self: self.d(resourceId="com.ichi2.anki:id/fab_main").exists
    )
    def test_create_deck(self):
        self.d(resourceId="com.ichi2.anki:id/fab_main").click()
        sleep(0.5)
        self.d(resourceId='com.ichi2.anki:id/add_deck_label').click()
        sleep(0.5)
        random_text = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        self.d(resourceId='com.ichi2.anki:id/dialog_text_input').set_text(random_text)
        sleep(0.5)
        self.d(text='OK').click()

    @precondition(
        lambda self: self.d(resourceId="com.ichi2.anki:id/deckpicker_new").exists
    )
    def test_increase_new_card_limit(self):
        original_num = int(self.d(resourceId='com.ichi2.anki:id/deckpicker_new').get_text())
        print(f"Original new cards count on main screen: {original_num}")
        self.d(resourceId='com.ichi2.anki:id/deckpicker_name').long_click()
        sleep(0.5)
        self.d(text='Custom study').click()
        sleep(2)
        self.d(text='Increase today\'s new card limit').click()
        detail_text = self.d(resourceId='com.ichi2.anki:id/custom_study_details_text1').get_text()
        print(f"Raw detail text: '{detail_text}'")
        match = re.search(r'(\d+)', detail_text)
        available_limit = int(match.group(1))
        print(f"Parsed available limit: {available_limit}")
        update_val = get_random_new_card_limit()
        print(f"Randomly generated value to input: {update_val}")
        self.d(resourceId='com.ichi2.anki:id/custom_study_details_edittext2').set_text(update_val)
        self.d(text='OK').click()
        sleep(1)
        new_num = int(self.d(resourceId='com.ichi2.anki:id/deckpicker_new').get_text())
        print(f"Final new cards count on main screen: {new_num}")
        raw_total = original_num + update_val
        # Constraints:
        # Lower bound is always 0
        # Upper bound is the 'available_limit' extracted from the text
        lower_bound = 0
        upper_bound = available_limit
        # Final count cannot be less than 0 and cannot exceed available_limit
        expected_num = max(lower_bound, min(raw_total, upper_bound))
        print(f"Expected: clamped({original_num} + {update_val}) -> {expected_num}")
        assert new_num == expected_num



    @max_tries(1)
    @precondition(
        lambda self: self.d(text='Card types').exists
                     and self.d(resourceId="com.ichi2.anki:id/action_confirm").exists
    )
    def test_add_card_types(self):
        self.d(description='More options').click()
        sleep(0.5)
        self.d(text='Add').click()
        text = self.d(resourceId='android:id/message').get_text()
        match = re.search(r'\d+', text)
        if match:
            number = int(match.group())
            try:
                current = int(state.get('card_number', 0))
            except Exception:
                current = 0
            state['card_number'] = current + number
        self.d(text='OK').click()
        sleep(0.5)
        edit_text = self.d(resourceId='com.ichi2.anki:id/edit_text').get_text()
        edit_text += ''.join(random.choices("abc123XYZ", k=8))
        self.d(resourceId='com.ichi2.anki:id/edit_text').set_text(edit_text)
        new_card_type = add_card_type()
        print(new_card_type)
        self.d(description='Save').click()
        sleep(0.5)
        new_card_type = new_card_type.replace('\u2068', '?')
        print(new_card_type)
        print(self.d(resourceId="com.ichi2.anki:id/CardEditorCardsButton").get_text())
        print(new_card_type in self.d(resourceId="com.ichi2.anki:id/CardEditorCardsButton").get_text())
        assert new_card_type in self.d(resourceId="com.ichi2.anki:id/CardEditorCardsButton").get_text()

    @max_tries(1)
    @precondition(
        lambda self: self.d(text='Card types').exists
                     and self.d(resourceId="com.ichi2.anki:id/action_confirm").exists
                     and len(state['card_types']) > 1
    )
    def test_delete_card_types(self):
        delete_card_type = last_card_type()
        text_str = f'{delete_card_type}\u2069'
        self.d(text=text_str).click()
        sleep(1)
        self.d(description='More options').click()
        sleep(0.5)
        self.d(text='Delete').click()
        text = self.d(resourceId='android:id/message').get_text()
        match = re.search(r'its (\d+) cards', text)
        if match:
            number = int(match.group(1))
            try:
                current = int(state.get('card_number', 0))
                state['card_number'] = current - number
            except Exception:
                print("Error parsing card_number during deletion")
        self.d(text='OK').click()
        sleep(0.5)
        self.d(description='Save').click()
        pop_card_type()
        sleep(1)
        delete_card_type = delete_card_type.replace('\u2068', '?')
        print(delete_card_type)
        print(self.d(resourceId="com.ichi2.anki:id/CardEditorCardsButton").get_text())
        print(delete_card_type not in self.d(resourceId="com.ichi2.anki:id/CardEditorCardsButton").get_text())
        assert delete_card_type not in self.d(resourceId="com.ichi2.anki:id/CardEditorCardsButton").get_text()


    @precondition(
        lambda self: self.d(resourceId="com.ichi2.anki:id/deck_name").exists
                     and self.d(resourceId="com.ichi2.anki:id/subtitle").exists
    )
    def test_card_number(self):
        self.d(resourceId="com.ichi2.anki:id/deck_name").click()
        sleep(0.5)
        self.d(text="All decks").click()
        sleep(0.5)
        print(self.d(resourceId="com.ichi2.anki:id/subtitle").get_text())
        text = self.d(resourceId="com.ichi2.anki:id/subtitle").get_text()
        number = int(re.search(r'\d+', text).group())
        assert number == state['card_number']

    @max_tries(1)
    @precondition(
        lambda self: self.d(resourceId="com.ichi2.anki:id/CardEditorTagButton").exists
    )
    def test_add_tags(self):
        self.d(resourceId="com.ichi2.anki:id/CardEditorTagButton").click()
        sleep(0.5)
        self.d(resourceId='com.ichi2.anki:id/tags_dialog_action_add').click()
        sleep(0.5)
        tag_name = ''.join(random.choices("abc123XYZ", k=8))
        self.d(resourceId='com.ichi2.anki:id/dialog_text_input').set_text(tag_name)
        sleep(0.5)
        self.d(text='OK').click()
        sleep(0.5)
        self.d(text='OK').click()
        state['tags'].append(tag_name)
        sleep(0.5)
        tag_text = self.d(resourceId='com.ichi2.anki:id/CardEditorTagButton').get_text()
        assert tag_name in tag_text

