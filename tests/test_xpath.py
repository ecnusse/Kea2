import unittest
from kea2.u2Driver import U2StaticChecker, U2StaticDevice
from pathlib import Path


XML_PATH = Path(__file__).parent / "xpath_test.xml"


class U2StaticCheckerForTest(U2StaticChecker):
    def __init__(self):
        self.d = U2StaticDevice(script_driver=None)


def get_static_checker():
    xml = ""
    with open(XML_PATH, "r", encoding="utf-8") as f:
        xml = f.read()
    d = U2StaticCheckerForTest()
    return d.getInstance(xml)


class TestXPath(unittest.TestCase):

    def setUp(self):
        self.d = get_static_checker()

    def test_basic_xpath(self):
        assert self.d.xpath("""//*[@text="Hrgshsjs"]""").exists
        assert self.d.xpath("""//android.widget.TextView[@text="hehzhe"]""").exists
        assert self.d.xpath(
            """(//*[@resource-id="it.feio.android.omninotes.alpha:id/category_marker"])[3]"""
        ).exists

        assert self.d.xpath('@com.android.systemui:id/clock').exists          

        assert self.d.xpath('//android.widget.TextView[@text="hehzhe"]')\
                    .parent_exists('//androidx.recyclerview.widget.RecyclerView')   

        assert (self.d.xpath('100') &
                self.d.xpath('@com.android.systemui:id/battery_inside_percent')).exists

        assert (self.d.xpath('100') | self.d.xpath('2:14')).exists            # |

        assert self.d.xpath('//android.widget.TextView[@text="Notes"]')\
                    .parent_exists('@it.feio.android.omninotes.alpha:id/toolbar')  # parent_exists

        assert self.d.xpath('@it.feio.android.omninotes.alpha:id/fab')\
                    .child('/android.widget.ImageButton').exists              # child

        assert self.d.xpath('//androidx.drawerlayout.widget.DrawerLayout[@resource-id="it.feio.android.omninotes.alpha:id/drawer_layout"]' +
                            '//android.view.ViewGroup[@resource-id="it.feio.android.omninotes.alpha:id/toolbar"]').exists

        assert self.d.xpath('(//android.view.View[@resource-id="it.feio.android.omninotes.alpha:id/category_marker"])[3]')\
                    .parent_exists('//androidx.recyclerview.widget.RecyclerView[@resource-id="it.feio.android.omninotes.alpha:id/list"]')
        
        assert self.d.xpath('//androidx.drawerlayout.widget.DrawerLayout[@resource-id="it.feio.android.omninotes.alpha:id/drawer_layout"]' +
                            '//android.view.ViewGroup[@resource-id="it.feio.android.omninotes.alpha:id/toolbar"]').exists

        # parent_exists
        node = (self.d.xpath('@com.android.systemui:id/battery_inside_percent') |  
                self.d.xpath('@com.android.systemui:id/clock'))                    
        assert node & self.d.xpath('//android.widget.TextView')                     
        assert node.parent_exists('@com.android.systemui:id/status_bar')            # parent_exists


if __name__ == "__main__":
    unittest.main()
