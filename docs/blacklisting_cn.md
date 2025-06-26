## 黑名单特定UI控件/区域（黑白名单/控件/界面特定区域）

[中文文档](blacklisting_cn.md)

Fastbot支持将特定UI控件或区域加入黑名单，以防止在模糊测试过程中与它们交互。

黑名单分为两个层级：

- **控件屏蔽**：用于禁用单个控件。
- **树屏蔽**：通过指定某个区域的根节点，禁用该区域下所有控件，即屏蔽整个子树。

我们提供两种类型的黑名单：

1. **全局黑名单** — 始终生效。
2. **条件黑名单** — 仅在满足特定条件时生效。

被屏蔽的元素配置在Kea2的配置文件 `configs/widget.block.py` 中（运行 `kea2 init` 时生成）。  
元素可灵活使用u2选择器（如 `text` 或 `description`）、XPath或其他选择器方式指定。

#### 控件屏蔽
##### 全局黑名单
可定义函数 `global_block_widgets` 来指定应全局屏蔽的UI控件。该屏蔽始终生效。

```python
# file: configs/widget.block.py

def global_block_widgets(d: "Device"):
    """
    全局黑名单。
    返回应该被全局屏蔽的控件列表
    """
    return [d(text="widgets to block"), 
            d.xpath(".//node[@text='widget to block']"),
            d(description="widgets to block")]
```

##### 条件黑名单
可定义任意以 "block_" 开头命名的保留函数（无需 "block_tree_" 前缀），并用 `@precondition` 装饰该函数，实现条件黑名单。  
此时，仅当满足前置条件时屏蔽生效。

```python
# file: configs/widget.block.py

# 条件黑名单
@precondition(lambda d: d(text="In the home page").exists)
def block_sth(d: "Device"):
    # 重要：函数名必须以 "block_" 开头
    return [d(text="widgets to block"), 
            d.xpath(".//node[@text='widget to block']"),
            d(description="widgets to block")]
```

#### 树屏蔽
##### 全局黑名单
可定义函数 `global_block_tree` 来指定应全局屏蔽的UI控件树。该屏蔽始终生效。

```python
# file: configs/widget.block.py

def global_block_tree(d: "Device"):
    """
    指定在测试期间应全局屏蔽的UI控件树。
    返回根节点列表，整个子树将被屏蔽，不会被探索。
    该函数仅在'u2 agent'模式下可用。
    """
    return [d(text="trees to block"), d.xpath(".//node[@text='tree to block']")]
```

##### 条件黑名单
可定义任意以 "block_tree_" 开头命名的保留函数，并用 `@precondition` 装饰该函数，实现条件黑名单。  
此时，只有满足前置条件时屏蔽才生效。

```python
# file: configs/widget.block.py

# 带前置条件的条件树黑名单示例

@precondition(lambda d: d(text="In the home page").exists)
def block_tree_sth(d: "Device"):
    # 注意：函数名必须以 "block_tree_" 开头
    return [d(text="trees to block"), 
            d.xpath(".//node[@text='tree to block']"),
            d(description="trees to block")]
```

> 实现原理：  
> - 控件屏蔽：仅将指定控件的特定属性（clickable, long-clickable, scrollable, checkable, enabled, focusable）设置为False。  
> - 树屏蔽：将该控件作为子树根节点，将其及所有后代节点的上述属性全部设置为False。

### 支持的UI元素定位方法

配置黑名单时，可以通过组合多个属性精准定位当前窗口中特定的UI元素。属性可灵活组合使用，实现准确屏蔽。

例如，定位文本为 "Alarm" 且类名为 `android.widget.Button` 的UI元素：

```python
d(text="Alarm", className="android.widget.Button")
```

#### 支持的属性

常用属性如下，详细用法请参考官方 [Android UiSelector文档](http://developer.android.com/tools/help/uiautomator/UiSelector.html)：

- **文本相关属性**  
  `text`、`textContains`、`textStartsWith`

- **类相关属性**  
  `className`

- **描述相关属性**  
  `description`、`descriptionContains`、`descriptionStartsWith`

- **状态相关属性**  
  `checkable`、`checked`、`clickable`、`longClickable`、`scrollable`、`enabled`、`focusable`、`focused`、`selected`

- **包名相关属性**  
  `packageName`

- **资源ID相关属性**  
  `resourceId`

- **索引相关属性**  
  `index`

#### 定位子控件与兄弟控件

除了直接定位目标元素，还可以定位子控件或兄弟控件，用于更复杂查询。

- **定位子控件或孙子控件**  
  例如，定位列表中名为 "Wi-Fi" 的项：

  ```python
  d(className="android.widget.ListView").child(text="Wi-Fi")
  ```

- **定位兄弟控件**  
  例如，定位文本为 "Settings" 控件旁边的 `android.widget.ImageView` 兄弟控件：

  ```python
  d(text="Settings").sibling(className="android.widget.ImageView")
  ```

---

### 不支持的方法

> ⚠️ 请避免使用以下因**不支持**而可能导致黑名单配置失效的方法：

- 基于位置关系的查询：

  ```python
  d(A).left(B)    # 选中位于A左侧的B
  d(A).right(B)   # 选中位于A右侧的B
  d(A).up(B)      # 选中位于A上方的B
  d(A).down(B)    # 选中位于A下方的B
  ```

- child_by_text、child_by_description、child_by_instance等子控件查询方法，例如：

  ```python
  d(className="android.widget.ListView", resourceId="android:id/list") \
    .child_by_text("Bluetooth", className="android.widget.LinearLayout")
  
  d(className="android.widget.ListView", resourceId="android:id/list") \
    .child_by_text(
      "Bluetooth",
      allow_scroll_search=True,  # 默认为False
      className="android.widget.LinearLayout"
    )
  ```

- 使用instance参数进行定位，例如：

  ```python
  d(className="android.widget.Button", instance=2)
  ```

- 正则表达式匹配参数：  
  `textMatches`、`classNameMatches`、`descriptionMatches`、`packageNameMatches`、`resourceIdMatches`

请避免使用以上不支持的方法，以确保黑名单配置生效。

## Activity黑名单与白名单配置

*(适用场景：针对部分Activity选择性覆盖或屏蔽不必要Activity)*

我们采用Fastbot的配置方式，进行了更友好的封装。  
允许用户在运行命令时直接指定设备读取黑白名单的路径，  
并展示执行的是黑名单还是白名单（两者只能选择其一）。  
只需填好黑白名单文件，并在运行命令指定执行哪个（及设备上的路径），  
无需手动推送文件到设备，我们会帮你自动推送到指定设备路径。

### Activity白名单配置

1. **添加Activity名称**  
   将你想加入白名单的Activity名写入 `configs/awl.strings`。

   **示例：**
   ```
   it.feio.android.omninotes.MainActivity
   it.feio.android.omninotes.SettingsActivity
   ```

  > 注意：无需手动推送白名单文件至设备，我们会自动处理。

2. **运行测试时添加参数**

   添加如下参数，指定白名单文件路径（如设备上的 `/sdcard/awl.strings`）：
   ```
   --act-whitelist-file /sdcard/awl.strings
   ```

   运行示例命令：
   ```
   kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --act-whitelist-file /sdcard/awl.strings --driver-name d unittest discover -p quicktest.py
   ```

### Activity黑名单配置

1. **添加Activity名称**  
   将你想加入黑名单的Activity名写入 `configs/abl.strings`，格式同白名单。

   **示例：**
   ```
   it.feio.android.omninotes.MainActivity
   it.feio.android.omninotes.SettingsActivity
   ```

> 注意：无需手动推送黑名单文件至设备，我们会自动处理。

2. **运行测试时添加参数**

   添加如下参数，指定黑名单文件路径（如设备上的 `/sdcard/abl.strings`）：
   ```
   --act-blacklist-file /sdcard/abl.strings
   ```

   运行示例命令：
   ```
   kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --act-blacklist-file /sdcard/abl.strings --driver-name d unittest discover -p quicktest.py
   ```

### 重要说明
- 白名单和黑名单**不可同时设置**，遵循“白名单或黑名单”原则。若设置了白名单，则白名单外所有Activity均视为黑名单。  
- 通过Fastbot的hook机制，对Activity启动和切换进行监控。若即将进入黑名单中的Activity，则启动动作会被阻断，界面看起来对应切换动作无响应。