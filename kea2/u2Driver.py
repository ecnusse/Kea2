import functools
from time import sleep
from importlib.metadata import version

import uiautomator2 as u2
import adbutils
import types
import rtree
import re

from typing import List, Literal, Union, Optional
from lxml import etree
from packaging.version import Version
from .adbUtils import list_forwards, remove_forward
from .utils import getLogger


import logging
logging.getLogger("urllib3").setLevel(logging.INFO)
logging.getLogger("uiautomator2").setLevel(logging.INFO)

logger = getLogger(__name__) 

"""
The definition of U2ScriptDriver
"""
class U2ScriptDriver:
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
        logger.debug("U2Driver tearDown: stop_uiautomator")
        if self.d is None:
            return
        try:
            self.d._device_server_port = 9008
            self.d.stop_uiautomator()
        except (OSError, AttributeError, RuntimeError) as e:
            logger.debug(f"Error during uiautomator teardown (may be already closed): {e}")
        except Exception as e:
            logger.warning(f"Unexpected error during uiautomator teardown: {e}")

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


class StaticXpathObject(u2.xpath.XPathSelector):
    pass

"""
The definition of XpathStaticChecker
"""
class StaticXpathObjectV1(StaticXpathObject):
    def __init__(self, session, selector):
        self.session: U2StaticDevice = session
        self.selector = selector

    @property
    def exists(self):
        source = self.session.get_page_source()
        return len(self.selector.all(source)) > 0

    def __and__(self, value) -> 'StaticXpathObject':
        s = u2.xpath.XPathSelector(self.selector)
        s._next_xpath = u2.xpath.XPathSelector.create(value.selector)
        s._operator = u2.xpath.Operator.AND
        s._parent = self.selector._parent
        self.selector = s
        return self

    def __or__(self, value) -> 'StaticXpathObject':
        s = u2.xpath.XPathSelector(self.selector)
        s._next_xpath = u2.xpath.XPathSelector.create(value.selector)
        s._operator = u2.xpath.Operator.OR
        s._parent = self.selector._parent
        self.selector = s
        return self

    def selector_to_xpath(self, selector: u2.xpath.XPathSelector) -> str:
        """
            Convert an XPathSelector to a standard XPath expression.

            Args:
                selector: The XPathSelector object to convert.

            Returns:
                A standard XPath expression as a string.
            """

        def _handle_path(path):
            if isinstance(path, u2.xpath.XPathSelector):
                return self.selector_to_xpath(path)
            elif isinstance(path, u2.xpath.XPath):
                return str(path)
            else:
                return path

        base_xpath = _handle_path(selector._base_xpath)
        base_xpath = base_xpath.replace('//*', './/node')

        if selector._operator is None:
            return base_xpath
        else:
            print("Unsupported operator: {}".format(selector._operator))
            return "//error"

    def xpath(self, _xpath: Union[list, tuple, str]) -> 'StaticXpathObject':
        """
        add xpath to condition list
        the element should match all conditions

        Deprecated, using a & b instead
        """
        if isinstance(_xpath, (list, tuple)):
            self.selector = functools.reduce(lambda a, b: a & b, _xpath, self)
        else:
            self.selector = self.selector & _xpath
        return self

    def child(self, _xpath: str) -> "StaticXpathObject":
        """
        add child xpath
        """
        if self.selector._operator or not isinstance(self.selector._base_xpath, u2.xpath.XPath):
            raise u2.xpath.XPathError("can't use child when base is not XPath or operator is set")
        new = self.selector.copy()
        new._base_xpath = self.selector._base_xpath.joinpath(_xpath)
        self.selector = new
        return self

    def get(self, timeout=None) -> "u2.xpath.XMLElement":
        """
        Get first matched element

        Args:
            timeout (float): max seconds to wait

        Returns:
            XMLElement

        """
        if not self.exists:
            return None
        return self.get_last_match()

    def get_last_match(self) -> "u2.xpath.XMLElement":
        return self.selector.all(self.selector._last_source)[0]

    def parent_exists(self, xpath: Optional[str] = None):
        el = self.get()
        if el is None:
            return False
        element = el.parent(xpath) if hasattr(el, 'parent') else None
        return True if element is not None else False

    def __getattr__(self, key: str):
        """
              In IPython console, attr:_ipython_canary_method_should_not_exist_ will be called
              So here ignore all attr startswith _
              """
        if key.startswith("_"):
            raise AttributeError("Invalid attr", key)
        if not hasattr(u2.xpath.XMLElement, key):
            raise AttributeError("Invalid attr", key)
        return getattr(super(), key)


class StaticXpathObjectV2(StaticXpathObjectV1):
    def __and__(self, value) -> 'StaticXpathObject':
        s = u2.xpath.XPathSelector(self.selector)
        s._next_xpath = u2.xpath.XPathSelector.create(value.selector)
        s._operator = u2.xpath.Operator.AND
        self.selector = s
        return self

    def __or__(self, value) -> 'StaticXpathObject':
        s = u2.xpath.XPathSelector(self.selector)
        s._next_xpath = u2.xpath.XPathSelector.create(value.selector)
        s._operator = u2.xpath.Operator.OR
        self.selector = s
        return self

    def get_last_match(self) -> "u2.xpath.XMLElement":
        source = self.session.get_page_source()
        return self.selector.all(source)[0]


class StaticXpathUiObjectFactory:

    _u2_version = None

    @classmethod
    def get_u2_version(cls):
        if cls._u2_version is None:
            cls._u2_version = Version(version("uiautomator2"))
        return cls._u2_version

    @classmethod
    def create(cls, session, xpath, source) -> StaticXpathObject:
        if cls.get_u2_version() <= Version("3.4.0"):
            return StaticXpathObjectV1(session, selector=u2.xpath.XPathSelector(xpath, source=source))
        elif cls.get_u2_version() >= Version("3.4.1"):
            return StaticXpathObjectV2(session, selector=u2.xpath.XPathSelector(xpath))


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
        try:
            self.set_covered_attr(root)
        except Exception as e:
            import traceback, uuid
            traceback.print_exc()
            logger.error(f"Error in setting covered widgets")
            from .utils import LoggingLevel
            if LoggingLevel.level <= logging.DEBUG:
                with open(f"kea2_error_tree_{uuid.uuid4().hex}.xml", "wb") as f:
                    xml_bytes = etree.tostring(root, pretty_print=True, encoding="utf-8", xml_declaration=True)
                    f.write(xml_bytes)

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
        self._script_driver:u2.Device = script_driver
        self._app_current = None

    def __call__(self, **kwargs):
        ui = StaticU2UiObject(session=self, selector=u2.Selector(**kwargs))
        if self._script_driver:
            ui.jsonrpc = self._script_driver.jsonrpc
        return ui

    def clear_cache(self):
        self._app_current = None

    def app_current(self):
        if not self._app_current:
            self._app_current = self._script_driver.app_current()
        return self._app_current

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
        ui = StaticXpathUiObjectFactory.create(session=self, xpath=xpath, source=source)
        return ui


class U2StaticChecker:
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
        self.d.clear_cache()
        self.setHierarchy(hierarchy)
        return self.d


"""
The definition of U2Driver
"""
class U2Driver:
    scriptDriver = None
    staticChecker = None

    @classmethod
    def setDevice(cls, kwarg):
        if kwarg.get("serial"):
            U2ScriptDriver.setDeviceSerial(kwarg["serial"])
        if kwarg.get("transport_id"):
            U2ScriptDriver.setTransportId(kwarg["transport_id"])

    @classmethod
    def getScriptDriver(cls, mode:Literal["direct", "proxy"]="proxy") -> u2.Device:
        """
        get the uiautomator2 device instance
        mode: direct or proxy
        direct: connect to device directly (device server port: 9008)
        proxy: connect to device via kea2 agent (device server port: 8090)
        """
        if cls.scriptDriver is None:
            cls.scriptDriver = U2ScriptDriver()
        _instance = cls.scriptDriver.getInstance()
        _instance._device_server_port = 9008 if mode == "direct" else 8090
        return _instance

    @classmethod
    def getStaticChecker(self, hierarchy=None):
        if self.staticChecker is None:
            self.staticChecker = U2StaticChecker()
        
        return self.staticChecker.getInstance(hierarchy)

    @classmethod
    def tearDown(self):
        if self.scriptDriver:
            try:
                self.scriptDriver.tearDown()
            except Exception as e:
                logger.debug(f"Error during U2Driver teardown: {e}")


"""
Other Utils
"""
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
