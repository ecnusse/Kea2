## Blacklisting specific UI widgets/regions (黑白名单/控件/界面特定区域)

[中文文档](blacklisting_cn.md)


Fastbot supports blacklisting specific UI widgets or regions to prevent interactions with them during fuzzing.

There are two levels of blacklisting:

- **Widget Blocking:** Use this to disable individual widgets.
- **Tree Blocking:** Use this to disable all widgets within a specific area by specifying the root node of that area, thereby blocking the entire subtree of widgets under it.

We provide two types of block lists:

1. **Global Block List** — always in effect.
2. **Conditional Block List** — effective only when certain conditions are met.

Blocked elements are configured in Kea2’s config file `configs/widget.block.py` (generated when running `kea2 init`).  
Elements can be flexibly specified using u2 selectors (such as `text` or `description`), XPath, or other selector methods. 


#### Widget Blocking
##### Global Block List
We can define the function `global_block_widgets` to specify which UI widgets should be blocked globally. The blocking always takes effect. 

```python
# file: configs/widget.block.py

def global_block_widgets(d: "Device"):
    """
    global block list.
    return the widgets which should be blocked globally
    """
    return [d(text="widgets to block"), 
            d.xpath(".//node[@text='widget to block']"),
            d(description="widgets to block")]
```
##### Conditional Block List
We can define any reserved function whose name starts with "block_" (but not requiring "block_tree_" prefix) and decorate such function by `@precondition` to allow conditional block list.
In this case, the blocking only takes effect when the precondition is satisfied.
```python
# file: configs/widget.block.py

# conditional block list
@precondition(lambda d: d(text="In the home page").exists)
def block_sth(d: "Device"):
    # Important: the function name should start with "block_"
    return [d(text="widgets to block"), 
            d.xpath(".//node[@text='widget to block']"),
            d(description="widgets to block")]
```

#### Tree Blocking
##### Global Block List
We can define the function `global_block_tree` to specify which UI widget trees should be blocked globally. The blocking always takes effect. 

```python
# file: configs/widget.block.py

def global_block_tree(d: "Device"):
    """
    Specify UI widget trees to be blocked globally during testing.
    Returns a list of root nodes whose entire subtrees will be blocked from exploration.
    This function is only available in 'u2 agent' mode.
    """
    return [d(text="trees to block"), d.xpath(".//node[@text='tree to block']")]
```
##### Conditional Block List
We can define any reserved function whose name starts with "block_tree_" and decorate such function by `@precondition` to allow conditional block list.
In this case, the blocking only takes effect when the precondition is satisfied.
```python
# file: configs/widget.block.py

# Example of conditional tree blocking with precondition

@precondition(lambda d: d(text="In the home page").exists)
def block_tree_sth(d: "Device"):
    # Note: Function name must start with "block_tree_"
    return [d(text="trees to block"), 
            d.xpath(".//node[@text='tree to block']"),
            d(description="trees to block")]
```

> Implementation principle:
> - Widget Blocking: Set only the specified attributes (clickable, long-clickable, scrollable, checkable, enabled, focusable) of the given widget to false.
> - Tree Blocking: Treat the given widget as the root of a subtree, and set the above attributes to false for the root widget as well as all its descendant nodes within that subtree.


### Supported Methods for UI Element Identification

When configuring the blacklist, you can precisely locate specific UI elements in the current window by combining various attributes. These attributes can be flexibly used together to achieve accurate blocking.

For example, to locate a UI element with text "Alarm" and class name `android.widget.Button`:

```python
d(text="Alarm", className="android.widget.Button")
```

#### Supported Attributes

Commonly used attributes are listed below. For detailed usage, please refer to the official [Android UiSelector documentation](http://developer.android.com/tools/help/uiautomator/UiSelector.html):

- **Text-related attributes**  
  `text`, `textContains`, `textStartsWith`

- **Class-related attributes**  
  `className`

- **Description-related attributes**  
  `description`, `descriptionContains`, `descriptionStartsWith`

- **State-related attributes**  
  `checkable`, `checked`, `clickable`, `longClickable`, `scrollable`, `enabled`, `focusable`, `focused`, `selected`

- **Package name related attributes**  
  `packageName`

- **Resource ID related attributes**  
  `resourceId`

- **Index related attributes**  
  `index`

#### Locating Children and Siblings

Besides directly locating target elements, you can locate child or sibling elements for more complex queries.

- **Locate child or grandchild elements**  
  For example, locate an item named "Wi-Fi" inside a list view:

  ```python
  d(className="android.widget.ListView").child(text="Wi-Fi")
  ```

- **Locate sibling elements**  
  For example, find an `android.widget.ImageView` sibling next to an element with text "Settings":

  ```python
  d(text="Settings").sibling(className="android.widget.ImageView")
  ```

#### XPath Expressions:
- Basic XPath Expressions:
  ```python
    d.xpath('//*[@text="Private FM"]')
    ```

- Starting with @:
    ```python
     d.xpath('@personal-fm') # Equivalent to d.xpath('//*[@resource-id="personal-fm"]').exists
    ```
  
- Child Element Positioning:
    ```python
     d.xpath('@android:id/list').child('/android.widget.TextView')
    ```
---

### Unsupported Methods

> ⚠️ Please avoid using the following methods as they are **not supported** for blacklist configuration:

- Positional relations based queries:  

  ```python
  d(A).left(B)    # Select B to the left of A
  d(A).right(B)   # Select B to the right of A
  d(A).up(B)      # Select B above A
  d(A).down(B)    # Select B below A
  ```

- Child querying methods such as `child_by_text`, `child_by_description`, and `child_by_instance`. For example:

  ```python
  d(className="android.widget.ListView", resourceId="android:id/list") \
    .child_by_text("Bluetooth", className="android.widget.LinearLayout")
  
  d(className="android.widget.ListView", resourceId="android:id/list") \
    .child_by_text(
      "Bluetooth",
      allow_scroll_search=True,  # default False
      className="android.widget.LinearLayout"
    )
  ```
- Using instance parameter to locate elements. For example, avoid:

 ```python
    d(className="android.widget.Button", instance=2)
  ```

- Regular expression matching parameters:  
  `textMatches`, `classNameMatches`, `descriptionMatches`, `packageNameMatches`, `resourceIdMatches`

#### XPath Expressions:
- Multiple Condition Positioning

```python
d.xpath('//android.widget.Button').xpath('//*[@text="Private FM"]')
```

- Parent Element Positioning

```python
d.xpath('//*[@text="Private FM"]').parent() # Position to the parent element
d.xpath('//*[@text="Private FM"]').parent("@android:list") # Position to the parent element that meets the condition
```

- Logical AND Queries

```python
(d.xpath("NFC") & d.xpath("@android:id/item"))
```

- Logical OR Queries

```python
(d.xpath("NFC") | d.xpath("App") | d.xpath("Content"))
```


Please avoid using these unsupported methods to ensure your blacklist configurations are applied correctly.


## Activity Blacklist and Whitelist Configuration

*(Applicable scenarios: selectively override certain activities or block unnecessary ones.)*

We adopt Fastbot's configuration method in a more user-friendly way. 
It allows users to specify the path for the device to read blacklists or whitelists directly in the running command and 
display whether they'll execute a blacklist or whitelist (only one can be chosen). 
You only need to fill in the blacklist/whitelist and specify in the running command which one to execute along with the path on the device. 
Once specified, you don't need to push the file to the device yourself; we'll handle the pushing to the designated device path for you.

### Activity Whitelist Configuration

1. **Add Activity names**  
   Write the names of Activities you want to whitelist into `configs/awl.strings`.

   **Example:** 
  ```
  it.feio.android.omninotes.MainActivity
  it.feio.android.omninotes.SettingsActivity
  ```

   
  > Note: You do not need to push the whitelist file to device. We will take care of this for you.


2. **Add parameter when running tests**  

   Add the following argument to specify the whitelist file (`/sdcard/awl.strings` is the desired path on the device):  
   ```
   --act-whitelist-file /sdcard/awl.strings
   ```
   
   Example command to run
   ```
   kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 --throttle 200 --act-whitelist-file /sdcard/awl.strings --driver-name d unittest discover -p quicktest.py
   ```

### Activity Blacklist Configuration

1. **Add Activity names**  
   Write the names of Activities you want to blacklist into `configs/abl.strings`, same format as whitelist.

      **Example:** 
  ```
  it.feio.android.omninotes.MainActivity
  it.feio.android.omninotes.SettingsActivity
  ```
>Note: You do not need to push the blacklist file to device. We will take care of this for you.


2. **Add parameter when running tests**  
   Add the following argument to specify the blacklist file (`/sdcard/abl.strings` is the desired path on the device):  
   ```
   --act-blacklist-file /sdcard/abl.strings
   ```
   
   Example command to run
   ```
   kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 --throttle 200 --act-blacklist-file /sdcard/abl.strings --driver-name d unittest discover -p quicktest.py
   ```


### Important Notes
- Whitelist and blacklist **cannot be set at the same time**. It follows the principle: either whitelist or blacklist. If a whitelist is set, all activities outside of it are considered blacklisted.
- Through hook in Fastbot, activity launches and switches are monitored. If a blacklisted activity is about to launch, the launch will be blocked, which makes the UI seem unresponsive to the transition action.


