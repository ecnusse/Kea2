import random
import socket
from time import sleep
import uiautomator2 as u2
import adbutils
import types
import rtree
import re
from typing import Any, Dict, List, Union, Optional
from http.client import HTTPResponse
from lxml import etree
from .absDriver import AbstractScriptDriver, AbstractStaticChecker, AbstractDriver
from .adbUtils import list_forwards, remove_forward, create_forward
from .utils import TimeStamp, getLogger

TIME_STAMP = TimeStamp().getTimeStamp()

import logging
logging.getLogger("urllib3").setLevel(logging.INFO)
logging.getLogger("uiautomator2").setLevel(logging.INFO)

logger = getLogger(__name__) 

"""
The definition of U2ScriptDriver
"""
class U2ScriptDriver(AbstractScriptDriver):
    """
    This is the ScriptDriver used to send ui automation request in Property
    When you interact with the mobile in properties. You will use the object here
    
    *e.g. the following self.d use U2ScriptDriver*
    ```
    @precondition(...)
    def test_battery(self):
        self.d(text="battery").click()
    ```
    """

    deviceSerial: str = None
    transportId: str = None
    d = None

    @classmethod
    def setTransportId(cls, transportId):
        cls.transportId = transportId

    @classmethod
    def setDeviceSerial(cls, deviceSerial):
        cls.deviceSerial = deviceSerial

    def getInstance(self):
        if self.d is None:
            adb = adbutils.device(serial=self.deviceSerial, transport_id=self.transportId)
            print("[INFO] Connecting to uiautomator2. Please wait ...")
            self.d = u2.connect(adb)
            sleep(5)
            self.d._device_server_port = 8090

        return self.d

    def _remove_remote_port(self, port:int):
        """remove the forward port
        """
        forwardLists = list_forwards(device=self.deviceSerial)
        for forward in forwardLists:
            if forward["remote"] == f"tcp:{port}":
                forward_local = forward["local"]
                remove_forward(local_spec=forward_local, device=self.deviceSerial)

    def tearDown(self):
        # logger.debug("U2Driver tearDown: stop_uiautomator")
        # self.d.stop_uiautomator()
        # logger.debug("U2Driver tearDown: remove forward")
        # self._remove_remote_port(8090)
        pass

"""
The definition of U2StaticChecker
"""
class StaticU2UiObject(u2.UiObject):
    def __init__(self, session, selector):
        self.session: U2StaticDevice = session
        self.selector = selector

    def _transferU2Keys(self, originKey):
        filterDict = {
            "resourceId": "resource-id",
            "description": "content-desc",
            "className": "class",
            "longClickable": "long-clickable",
        }
        if filterDict.get(originKey, None):
            return filterDict[originKey]
        return originKey

    def selector_to_xpath(self, selector: u2.Selector, is_initial: bool = True) -> str:
        """
            Convert a u2 Selector into an XPath expression compatible with Java Android UI controls.

            Args:
                selector (u2.Selector): A u2 Selector object
                is_initial (bool): Whether it is the initial node, defaults to True

            Returns:
                str: The corresponding XPath expression
            """
        try:

            xpath = ".//node" if is_initial else "node"

            conditions = []

            if "className" in selector:
                conditions.insert(0, f"[@class='{selector['className']}']")

            if "text" in selector:
                conditions.append(f"[@text='{selector['text']}']")
            elif "textContains" in selector:
                conditions.append(f"[contains(@text, '{selector['textContains']}')]")
            elif "textStartsWith" in selector:
                conditions.append(f"[starts-with(@text, '{selector['textStartsWith']}')]")
            elif "textMatches" in selector:
                raise NotImplementedError("'textMatches' syntax is not supported")

            if "description" in selector:
                conditions.append(f"[@content-desc='{selector['description']}']")
            elif "descriptionContains" in selector:
                conditions.append(f"[contains(@content-desc, '{selector['descriptionContains']}')]")
            elif "descriptionStartsWith" in selector:
                conditions.append(f"[starts-with(@content-desc, '{selector['descriptionStartsWith']}')]")
            elif "descriptionMatches" in selector:
                raise NotImplementedError("'descriptionMatches' syntax is not supported")

            if "packageName" in selector:
                conditions.append(f"[@package='{selector['packageName']}']")
            elif "packageNameMatches" in selector:
                raise NotImplementedError("'packageNameMatches' syntax is not supported")

            if "resourceId" in selector:
                conditions.append(f"[@resource-id='{selector['resourceId']}']")
            elif "resourceIdMatches" in selector:
                raise NotImplementedError("'resourceIdMatches' syntax is not supported")

            bool_props = ["checkable", "checked", "clickable", "longClickable", "scrollable", "enabled", "focusable",
                          "focused", "selected", "covered"]

            def str_to_bool(value):
                """Convert string 'true'/'false' to boolean, or return original value if already boolean"""
                if isinstance(value, str):
                    return value.lower() == "true"
                return bool(value)

            for prop in bool_props:
                if prop in selector:
                    bool_value = str_to_bool(selector[prop])
                    value = "true" if bool_value else "false"
                    conditions.append(f"[@{prop}='{value}']")

            if "index" in selector:
                conditions.append(f"[@index='{selector['index']}']")

            xpath += "".join(conditions)

            if "childOrSibling" in selector and selector["childOrSibling"]:
                for i, relation in enumerate(selector["childOrSibling"]):
                    sub_selector = selector["childOrSiblingSelector"][i]
                    sub_xpath = self.selector_to_xpath(sub_selector, False)

                    if relation == "child":
                        xpath += f"//{sub_xpath}"
                    elif relation == "sibling":
                        cur_root = xpath
                        following_sibling = cur_root + f"/following-sibling::{sub_xpath}"
                        preceding_sibling = cur_root + f"/preceding-sibling::{sub_xpath}"
                        xpath = f"({following_sibling} | {preceding_sibling})"
            if "instance" in selector:
                xpath = f"({xpath})[{selector['instance'] + 1}]"

            return xpath

        except Exception as e:
            print(f"Error occurred during selector conversion: {e}")
            return "//error"


    @property
    def exists(self):
        set_covered_to_deepest_node(self.selector)
        xpath = self.selector_to_xpath(self.selector)
        matched_widgets = self.session.xml.xpath(xpath)
        return bool(matched_widgets)

    def __len__(self):
        xpath = self.selector_to_xpath(self.selector)
        matched_widgets = self.session.xml.xpath(xpath)
        return len(matched_widgets)
    
    def child(self, **kwargs):
        return StaticU2UiObject(self.session, self.selector.clone().child(**kwargs))
    
    def sibling(self, **kwargs):
        return StaticU2UiObject(self.session, self.selector.clone().sibling(**kwargs))

    def __getattr__(self, attr):
        return getattr(super(), attr)

"""
The definition of XpathStaticChecker
"""
class StaticXpathUiObject(u2.UiObject):
    def __init__(self, session, selector):
        self.session: U2StaticDevice = session
        self.selector = selector

    @property
    def exists(self):
        return len(self.all()) > 0

    def all(self, source: Optional[u2.xpath.PageSource] = None) -> List["u2.xpath.XMLElement"]:
        """find all matched elements"""
        if not source:
            source = self.session.get_page_source()

        elements = []
        if isinstance(self.selector._base_xpath, u2.xpath.XPath):
            elements = source.find_elements(self.selector._base_xpath)
        else:
            elements = self.selector._base_xpath.all(source)

        # AND OR
        if self.selector._next_xpath and self.selector._operator:
            next_els = self.selector._next_xpath.all(source)
            if self.selector._operator == u2.xpath.Operator.AND:
                elements = list(set(elements) & set(next_els))
            elif self.selector._operator == u2.xpath.Operator.OR:
                elements = list(set(elements) | set(next_els))
            else:
                raise ValueError("Invalid operator", self.selector._operator)
        for el in elements:
            el._parent = self.selector._parent
        return elements

    def __getattr__(self, attr):
        return getattr(super(), attr)

def _get_bounds(raw_bounds):
    pattern = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")
    m = re.match(pattern, raw_bounds)
    try:
        bounds = [int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))]
    except Exception as e:
        print(f"raw_bounds: {raw_bounds}", flush=True)
        print(f"Please report this bug to Kea2", flush=True)
        raise RuntimeError(e)

    return bounds


class _HindenWidgetFilter:
    def __init__(self, root: etree._Element):
        # self.global_drawing_order = 0
        self._nodes = []

        self.idx = rtree.index.Index()
        self.set_covered_attr(root)

        # xml_bytes = etree.tostring(root, pretty_print=True, encoding="utf-8", xml_declaration=True)
        # with open("filtered_tree.xml", "wb") as f:
        #     f.write(xml_bytes)
        # xml_bytes

    def _iter_by_drawing_order(self, ele: etree._Element):
        """
        iter by drawing order (DFS)
        """
        if ele.tag == "node":
            yield ele

        children = list(ele)
        try:
            children.sort(key=lambda e: int(e.get("drawing-order", 0)))
        except (TypeError, ValueError):
            pass

        for child in children:
            yield from self._iter_by_drawing_order(child)
   
    def set_covered_attr(self, root: etree._Element):
        self._nodes: List[etree._Element] = list()
        for e in self._iter_by_drawing_order(root):
            # e.set("global-order", str(self.global_drawing_order))
            # self.global_drawing_order += 1
            e.set("covered", "false")

            # algorithm: filter by "clickable"
            clickable = (e.get("clickable", "false") == "true")
            _raw_bounds = e.get("bounds")
            if _raw_bounds is None:
                continue
            bounds = _get_bounds(_raw_bounds)
            if clickable:
                covered_widget_ids = list(self.idx.contains(bounds))
                if covered_widget_ids:
                    for covered_widget_id in covered_widget_ids:
                        node = self._nodes[covered_widget_id]
                        node.set("covered", "true")
                        self.idx.delete(
                            covered_widget_id,
                            _get_bounds(self._nodes[covered_widget_id].get("bounds"))
                        )

            cur_id = len(self._nodes)
            center = [
                (bounds[0] + bounds[2]) / 2,
                (bounds[1] + bounds[3]) / 2
            ]
            self.idx.insert(
                cur_id,
                (center[0], center[1], center[0], center[1])
            )
            self._nodes.append(e)


class U2StaticDevice(u2.Device):
    def __init__(self, script_driver=None):
        self.xml: etree._Element = None
        self._script_driver = script_driver

    def __call__(self, **kwargs):
        ui = StaticU2UiObject(session=self, selector=u2.Selector(**kwargs))
        if self._script_driver:
            ui.jsonrpc = self._script_driver.jsonrpc
        return ui

    @property
    def xpath(self) -> u2.xpath.XPathEntry:
        def get_page_source(self):
            # print("[Debug] Using static get_page_source method")
            xml_raw = etree.tostring(self._d.xml, encoding='unicode')
            return u2.xpath.PageSource.parse(xml_raw)
        xpathEntry = _XPathEntry(self)
        xpathEntry.get_page_source = types.MethodType(
            get_page_source, xpathEntry
        )
        return xpathEntry
    
    def __getattr__(self, attr):
        """Proxy other methods to script_driver"""
        logger.debug(f"{attr} not exists in static checker, proxy to script_driver.")
        return getattr(self._script_driver, attr)

class _XPathEntry(u2.xpath.XPathEntry):
    def __init__(self, d):
        self.xpath = None
        super().__init__(d)
        
    # def __call__(self, xpath, source = None):
        # TODO fully support xpath in widget.block.py
        # self.xpath = xpath
        # return super().__call__(xpath, source)
    def __call__(self, xpath, source=None):
        ui = StaticXpathUiObject(session=self, selector=u2.xpath.XPathSelector(xpath, source=source))
        return ui



class U2StaticChecker(AbstractStaticChecker):
    """
    This is the StaticChecker used to check the precondition.
    We use the static checker due to the performing issues when runing multi-properties.
    
    *e.g. the following self.d use U2StaticChecker*
    ```
    @precondition(lambda self: self.d("battery").exists)
    def test_battery(self):
        ...
    ```
    """
    def __init__(self):
        self.d = U2StaticDevice(U2ScriptDriver().getInstance()) 

    def setHierarchy(self, hierarchy: str):
        if hierarchy is None:
            return
        if isinstance(hierarchy, str):
            self.d.xml = etree.fromstring(hierarchy.encode("utf-8"))
        elif isinstance(hierarchy, etree._Element):
            self.d.xml = hierarchy
        elif isinstance(hierarchy, etree._ElementTree):
            self.d.xml = hierarchy.getroot()
        _HindenWidgetFilter(self.d.xml)

    def getInstance(self, hierarchy: str=None):
        self.setHierarchy(hierarchy)
        return self.d


"""
The definition of U2Driver
"""
class U2Driver(AbstractDriver):
    scriptDriver = None
    staticChecker = None

    @classmethod
    def setDevice(cls, kwarg):
        if kwarg.get("serial"):
            U2ScriptDriver.setDeviceSerial(kwarg["serial"])
        if kwarg.get("transport_id"):
            U2ScriptDriver.setTransportId(kwarg["transport_id"])

    @classmethod
    def getScriptDriver(self):
        if self.scriptDriver is None:
            self.scriptDriver = U2ScriptDriver()
        return self.scriptDriver.getInstance()

    @classmethod
    def getStaticChecker(self, hierarchy=None):
        if self.staticChecker is None:
            self.staticChecker = U2StaticChecker()
        return self.staticChecker.getInstance(hierarchy)

    @classmethod
    def tearDown(self):
        if self.scriptDriver:
            self.scriptDriver.tearDown()


"""
Other Utils
"""
def forward_port(self, remote: Union[int, str]) -> int:
        """forward remote port to local random port"""
        remote = 8090
        if isinstance(remote, int):
            remote = "tcp:" + str(remote)
        for f in self.forward_list():
            if (
                f.serial == self._serial
                and f.remote == remote
                and f.local.startswith("tcp:")
            ):  # yapf: disable
                return int(f.local[len("tcp:"):])
        local_port = get_free_port()
        self.forward("tcp:" + str(local_port), remote)
        logger.debug(f"forwading port: tcp:{local_port} -> {remote}")
        return local_port

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def get_free_port():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        try:
            return s.getsockname()[1]
        finally:
            s.close()
    except OSError:
        # bind 0 will fail on Manjaro, fallback to random port
        # https://github.com/openatx/adbutils/issues/85
        for _ in range(20):
            port = random.randint(10000, 20000)
            if not is_port_in_use(port):
                return port
        raise RuntimeError("No free port found")

def set_covered_to_deepest_node(selector: u2.Selector):

    def find_deepest_nodes(node):
        deepest_node = None
        is_leaf = True
        if "childOrSibling" in node and node["childOrSibling"]:
            for i, relation in enumerate(node["childOrSibling"]):
                sub_selector = node["childOrSiblingSelector"][i]
                deepest_node = find_deepest_nodes(sub_selector)
                is_leaf = False

        if is_leaf:
            deepest_node = node
        return deepest_node

    deepest_node = find_deepest_nodes(selector)

    if deepest_node is not None:
        dict.update(deepest_node, {"covered": False})


