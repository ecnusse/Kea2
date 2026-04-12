from kea2.utils import Device
from kea2.keaUtils import precondition


def global_block_widgets(d: "Device"):
    """
    Specify UI widgets to be blocked globally during testing.
    Returns a list of widgets that should be blocked from exploration.
    """
    # return [d(text="widgets to block"), d.xpath(".//node[@text='widget to block']")]
    return []


# Example of conditional blocking with precondition
# @precondition(lambda d: d(text="In the home page").exists)
@precondition(lambda d: False)
def block_sth(d: "Device"):
    # Note: Function name must start with "block_"
    return []


def global_block_tree(d: "Device"):
    """
    Specify UI widget trees to be blocked globally during testing.
    Returns a list of root nodes whose entire subtrees will be blocked from exploration.
    """
    # return [d(text="trees to block"), d.xpath(".//node[@text='tree to block']")]
    return []


# Example of conditional tree blocking with precondition
# @precondition(lambda d: d(text="In the home page").exists)
@precondition(lambda d: False)
def block_tree_sth(d: "Device"):
    # Note: Function name must start with "block_tree_"
    return []
