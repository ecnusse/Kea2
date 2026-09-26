"""
Flutter Gallery Test Properties for Kea2
Tests various Flutter widgets in the official Gallery app
"""
import unittest
import logging
import time

logger = logging.getLogger(__name__)

# Try to import u2_flutter, skip tests if not available
try:
    from u2_flutter import with_flutter
    HAS_U2_FLUTTER = True
except ImportError:
    HAS_U2_FLUTTER = False
    with_flutter = lambda func: func

from kea2 import precondition, prob

@unittest.skipIf(not HAS_U2_FLUTTER, "u2_flutter not installed")
class TestHybridApp(unittest.TestCase):
    """Test properties for Hybrid App (Phase 2: Native precondition -> Native action -> Flutter action)"""

    @with_flutter
    @prob(1.0)
    @precondition(lambda self: self.d(text="OPEN FLUTTER").exists)
    def test_native_to_flutter_flow(self):
        """
        Phase 2 demo: native precondition detects a real native control,
        clicks it, which navigates into the Flutter screen, then a Flutter
        action executes on that screen and verifies incremented tap count.
        """
        btn = self.d(text="OPEN FLUTTER")
        if btn.exists:
            btn.click()
            time.sleep(1.5)

        exists = self.flutter.find_by_key("HomeListView").exists
        logger.info(f"[RESULT] HomeListView exists = {exists}")
        assert exists, "Flutter screen did not load after native click"

        before_text = self.flutter.find_by_key("statusText").text
        logger.info(f"[RESULT] statusText before tap = {before_text}")
        before_count = int(before_text.split(":")[1].strip())

        self.flutter.find_by_key("actionButton").tap()
        logger.info("[RESULT] Tapped actionButton")
        time.sleep(0.5)

        after_text = self.flutter.find_by_key("statusText").text
        logger.info(f"[RESULT] statusText after tap = {after_text}")
        after_count = int(after_text.split(":")[1].strip())

        assert after_count == before_count + 1, \
            f"Expected tap count to increase by 1 (before={before_count}, after={after_count})"
        logger.info(f"[RESULT] Phase 2 flow completed successfully — tap count increased from {before_count} to {after_count}")
