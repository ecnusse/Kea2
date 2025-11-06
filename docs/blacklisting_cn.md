## Blacklisting specific UI widgets/regions (黑白名单/控件/界面特定区域)

[中文文档](docs/blacklisting_cn.md)

我们支持对特定 UI 控件/区域进行黑名单处理，从而阻止 Fastbot 在模糊测试过程中与这些控件交互。

我们支持两种粒度级别的黑名单：

- 控件屏蔽：屏蔽单个 UI 控件。
- 树屏蔽：通过指定根节点屏蔽一个 UI 控件树。它可以屏蔽根节点及其所有子节点。

我们支持（1）`全局黑名单`（始终生效）和（2）`条件黑名单`（仅在满足某些条件时生效）。

被屏蔽元素在 Kea2 的配置文件 `configs/widget.block.py` 中指定（此文件在运行 `kea2 init` 时生成）。  
需要屏蔽的元素可以灵活地通过 u2 选择器（例如 `text`、`description`）或 `xpath` 等指定。

#### 控件屏蔽
##### 全局黑名单
我们可以定义函数 `global_block_widgets`，指定哪些 UI 控件应被全局屏蔽。该屏蔽始终生效。

```python
# file: configs/widget.block.py

def global_block_widgets(d: "Device"):
    """
    全局黑名单。
    返回应被全局屏蔽的控件列表。
    """
    return [d(text="widgets to block"), 
            d.xpath(".//node[@text='widget to block']"),
            d(description="widgets to block")]
```
##### 条件黑名单
我们可以定义任意以 “block_” 开头（但不要求以 “block_tree_” 开头）的保留函数名，并使用 `@precondition` 装饰该函数，以支持条件黑名单。  
在这种情况下，屏蔽仅在前置条件满足时生效。

```python
# file: configs/widget.block.py

# 条件黑名单
@precondition(lambda d: d(text="In the home page").exists)
def block_sth(d: "Device"):
    # 重要：函数名应以 "block_" 开头
    return [d(text="widgets to block"), 
            d.xpath(".//node[@text='widget to block']"),
            d(description="widgets to block")]
```

#### 树屏蔽
##### 全局黑名单
我们可以定义函数 `global_block_tree`，指定哪些 UI 控件树应被全局屏蔽。该屏蔽始终生效。

```python
# file: configs/widget.block.py

def global_block_tree(d: "Device"):
    """
    指定测试过程中全局屏蔽的 UI 控件树。
    返回根节点列表，整个子树将被屏蔽不被探索。
    该函数仅在 'u2 agent' 模式下可用。
    """
    return [d(text="trees to block"), d.xpath(".//node[@text='tree to block']")]
```
##### 条件黑名单
我们可以定义任意以 “block_tree_” 开头的保留函数名，并使用 `@precondition` 装饰该函数，以支持条件黑名单。  
在这种情况下，屏蔽仅在前置条件满足时生效。

```python
# file: configs/widget.block.py

# 带前置条件的条件树屏蔽示例

@precondition(lambda d: d(text="In the home page").exists)
def block_tree_sth(d: "Device"):
    # 注意：函数名必须以 "block_tree_" 开头
    return [d(text="trees to block"), 
            d.xpath(".//node[@text='tree to block']"),
            d(description="trees to block")]
```

> 实现原理：
> - 控件屏蔽：将指定控件的特定属性（clickable, long-clickable, scrollable, checkable, enabled, focusable）设置为false。
> - 树屏蔽：将指定控件视为根节点，并将其自身及其所有子节点的上述属性设为false。

### 支持的UI控件定位方法

在配置黑名单时，你可以组合不同属性来精确定位当前屏幕上的特定UI控件。灵活运用这些属性能够帮助你准确地屏蔽某些控件。

此例子展示了如何定位一个显示文本为“Alarm”且类名为`android.widget.Button`的UI控件：

```python
d(text="Alarm", className="android.widget.Button")
```

#### 支持的属性

常见属性已在此列出。详细用法请参照官方[Android UI选择器文档](http://developer.android.com/tools/help/uiautomator/UiSelector.html)：

- **文本相关属性**  
  `text`, `textContains`, `textStartsWith`

- **类相关属性**  
  `className`

- **描述相关属性**  
  `description`, `descriptionContains`, `descriptionStartsWith`

- **状态相关属性**  
  `checkable`, `checked`, `clickable`, `longClickable`, `scrollable`, `enabled`, `focusable`, `focused`, `selected`

- **包名相关属性**  
  `packageName`

- **Resource ID相关属性**  
  `resourceId`

- **索引相关属性**  
  `index`

#### 定位子元素和兄弟元素

除了直接定位目标元素之外，你也可以定位子元素或兄弟元素以进行更复杂的查询。

- **定位直接或间接子元素**  
  此例子展示了如何定位一个在列表组件内部的文本为“Wi-Fi”的元素：

  ```python
  d(className="android.widget.ListView").child(text="Wi-Fi")
  ```

- **定位兄弟元素**  
  此例子展示了如何寻找一个与文本为“Settings”的元素相邻的 `android.widget.ImageView`元素。

  ```python
  d(text="Settings").sibling(className="android.widget.ImageView")
  ```

#### XPath表达式
- 基本XPath表达式：
  ```python
  d.xpath('//*[@text="Private FM"]')
  ```

- 以@开头：
  ```python
  d.xpath('@personal-fm') # 等价于 d.xpath('//*[@resource-id="personal-fm"]').exists
  ```

- 子元素定位：
  ```python
  d.xpath('@android:id/list').child('/android.widget.TextView')
  ```

---

### 不支持的UI控件定位方法

> ⚠️ 请避免使用下列方法，因为它们在黑名单配置中不被支持：

- 基于位置关系的查询：

  ```python
  d(A).left(B)    # 选择位于A左侧的B
  d(A).right(B)   # 选择位于A右侧的B
  d(A).up(B)      # 选择位于A上方的B
  d(A).down(B)    # 选择位于A下方的B
  ```

- 子元素查询方法，例如`child_by_text`, `child_by_description`以及`child_by_instance`等，如下所示：

  ```python
  d(className="android.widget.ListView", resourceId="android:id/list") \
    .child_by_text("Bluetooth", className="android.widget.LinearLayout")
  
  d(className="android.widget.ListView", resourceId="android:id/list") \
    .child_by_text(
      "Bluetooth",
      allow_scroll_search=True,  # 默认 False
      className="android.widget.LinearLayout"
    )
  ```
- 基于实例参数的方法，例如：

  ```python
  d(className="android.widget.Button", instance=2)
  ```

- 基于正则表达式匹配的方法：  
  `textMatches`, `classNameMatches`, `descriptionMatches`, `packageNameMatches`, `resourceIdMatches`

#### XPath表达式：
- 多条件定位

```python
d.xpath('//android.widget.Button').xpath('//*[@text="Private FM"]')
```

- 父元素定位

```python
d.xpath('//*[@text="Private FM"]').parent() # 定位到父元素
d.xpath('//*[@text="Private FM"]').parent("@android:list") # 定位到满足条件的父元素
```

- 逻辑与查询

```python
(d.xpath("NFC") & d.xpath("@android:id/item"))
```

- 逻辑或查询

```python
(d.xpath("NFC") | d.xpath("App") | d.xpath("Content"))
```

请避免使用这些不支持的方法，这样可以确保你的黑名单配置正确生效。

## Activity黑白名单配置

*（应用场景：有选择性地探索特定Activities，或屏蔽不需要探索的Activities）*

我们以一种更为用户友好的方式来使用Fastbot的页面黑白名单配置功能。  
通过命令行，用户可以显式指定黑白名单配置文件在设备上的存储路径，并且可以查看程序将执行黑名单还是白名单（只能选择其中一种）。  
你只需要填写黑名单/白名单配置文件，并在命令行中指定你要运行哪一种名单，以及配置文件在设备上的路径。  
一旦指定，你不需要手动将配置文件推送到设备上；程序将自动推送这些文件到你指定的设备路径中。

### Activity白名单配置

1. **添加Activity名称**  
   将你希望加入白名单的Activity名称写入 `configs/awl.strings`。

   **例子：** 
  ```
  it.feio.android.omninotes.MainActivity
  it.feio.android.omninotes.SettingsActivity
  ```

  > 注意：你不需要手动将此白名单文件推送到设备上，程序将自动完成这一工作。

2. **在运行测试时增加命令行参数**  

   在命令行添加以下参数以指定白名单文件 (`/sdcard/awl.strings`是设备上的目标路径):  
   ```
   --act-whitelist-file /sdcard/awl.strings
   ```
   
   示例运行命令：
   ```
   kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --act-whitelist-file /sdcard/awl.strings --driver-name d unittest discover -p quicktest.py
   ```

### Activity黑名单配置

1. **添加Activity名称**  
   将你希望加入黑名单的Activity名称写入`configs/abl.strings`，格式与白名单的相同。

   **例子：** 
  ```
  it.feio.android.omninotes.MainActivity
  it.feio.android.omninotes.SettingsActivity
  ```
> 注意：你不需要手动将此黑名单文件推送到设备上，程序将自动完成这一工作。

2. **在运行测试时增加命令行参数**  
   在命令行添加以下参数以指定黑名单文件 (`/sdcard/abl.strings`是设备上的目标路径):  
   
   ```
   --act-blacklist-file /sdcard/abl.strings
   ```
   
   示例运行命令：
   ```
   kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --act-blacklist-file /sdcard/abl.strings --driver-name d unittest discover -p quicktest.py
   ```

### 重要说明
- 白名单和黑名单**不能同时设置**。这符合一个原则：非黑即白。如果设置了白名单，那么所有不在白名单中的Activity将被视为在黑名单中。
- 通过Fastbot的钩子函数，程序可以监听activity的启动和切换。如果一个位于黑名单的activity将要启动，该启动过程会被阻塞，在此切换过程当中，UI页面看上去会失去响应。