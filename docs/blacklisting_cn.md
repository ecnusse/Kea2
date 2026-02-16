## Blacklisting specific UI widgets/regions (黑白名单/控件/界面特定区域)

黑名单定义了两个维度：范围（控件级别 vs 树级别）和规则类型（全局 vs 条件）。

#### 1. 范围（屏蔽什么）
**控件级别** — 屏蔽单个控件。  
**树级别** — 屏蔽一个控件及其整个子树（一个界面区域）。

#### 2. 规则类型（何时屏蔽）
**全局** — 在每个页面/界面上生效。  
**条件** — 仅在满足 `@precondition` 的页面上生效。

### 黑白名单控件/界面区域的 API

| 范围 \ 规则类型 | 全局（始终生效） | 条件（`@precondition`） |
|-|-|-|
| 控件级别 | `global_block_widgets` | `@precondition → block_*` |
| 树级别 | `global_block_tree` | `@precondition → block_tree_*` |

**示例见：** [:blue_book: widget.block.py](../kea2/assets/fastbot_configs/widget.block.py)

#### :white_check_mark: 支持的黑名单选择器

常用属性如下。详细用法请参考 [uiautomator2 文档](https://github.com/openatx/uiautomator2/)：

<details>
  <summary>基础选择器</summary>

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

- **Resource ID 相关属性**  
  `resourceId`

- **索引相关属性**  
  `index`
</details>

<details>
  <summary>子元素和兄弟元素选择器</summary>

- **定位子元素或孙元素**  

  ```python
  d(className="android.widget.ListView").child(text="Wi-Fi")
  ```

- **定位兄弟元素**  

  ```python
  d(text="Settings").sibling(className="android.widget.ImageView")
  ```
</details>

<details>
  <summary>基础 XPath 表达式</summary>

**基础用法**  
```python
d.xpath('//*[@text="Private FM"]')
```

**以 @ 开头**  
```python
d.xpath('@personal-fm')  # 等价于 d.xpath('//*[@resource-id="personal-fm"]').exists
```

**子元素定位**  
```python
d.xpath('@android:id/list').child('/android.widget.TextView')
```
</details>

#### :no_entry_sign: 不支持的黑名单选择器

请避免使用以下方法，因为它们**不支持**用于黑名单配置：

<details>
  <summary>基于位置关系的查询</summary>

```python
d(A).left(B)    # 选择 B，位于 A 的左侧
d(A).right(B)   # 选择 B，位于 A 的右侧
d(A).up(B)      # 选择 B，位于 A 的上方
d(A).down(B)    # 选择 B，位于 A 的下方
```
</details>

<details>
  <summary>子元素查询选择器</summary>

`child_by_text`, `child_by_description`, `child_by_instance`。
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
</details>

<details>
  <summary>instance 参数</summary>

```python
d(className="android.widget.Button", instance=2)
```
</details>

<details>
  <summary>基于正则表达式的查询</summary>

`textMatches`, `classNameMatches`, `descriptionMatches`, `packageNameMatches`, `resourceIdMatches`
</details>

<details>
  <summary>链式 XPath 选择器</summary>

基于父子关系的链式 XPath 选择器：
```python
d.xpath('//android.widget.Button').xpath('//*[@text="Private FM"]')
```

```python
d.xpath('//*[@text="Private FM"]').parent()  # 定位到父元素
d.xpath('//*[@text="Private FM"]').parent("@android:list")  # 定位到满足条件的父元素
```

带逻辑运算符的 XPath 选择器：
```python
(d.xpath("NFC") & d.xpath("@android:id/item"))
```

```python
(d.xpath("NFC") | d.xpath("App") | d.xpath("Content"))
```
</details>

---

## Activity 黑白名单配置

我们继承了 Fastbot 对 Activity 的黑白名单机制。使用该功能需要：

1. 在 `configs/awl.strings` 中指定需要加入黑名单或白名单的 Activity。
2. 运行 kea2 时添加对应参数（`--act-blacklist-file`、`--act-whitelist-file`）。

> `configs/awl.strings` 文件由 `kea2 init` 生成。[查看示例配置文件](/kea2/assets/fastbot_configs/abl.strings)

### Activity 黑白名单参数

| 参数 | 含义 | 默认路径 |
| --- | --- | --- |
| `--act-blacklist-file [路径]` | 启用 Activity 黑名单。若省略路径，默认使用 `/sdcard/.kea2/abl.strings`。 | `/sdcard/.kea2/abl.strings` |
| `--act-whitelist-file [路径]` | 启用 Activity 白名单。若省略路径，默认使用 `/sdcard/.kea2/awl.strings`。 | `/sdcard/.kea2/awl.strings` |

示例用法：
```
kea2 run -p it.feio.android.omninotes.alpha --act-blacklist-file propertytest discover -p quicktest.py

# 自定义黑名单文件路径
kea2 run -p it.feio.android.omninotes.alpha --act-blacklist-file /sdcard/custom_abl.strings propertytest discover -p quicktest.py
```

### Activity 黑白名单机制
- 白名单和黑名单**不能同时设置**。只能选择一种模式：如果设置了白名单，则所有不在白名单中的 Activity 都视为黑名单。
- Fastbot 会监听 Activity 启动。当一个黑名单中的 Activity 即将启动时，该启动会被阻止，因此 UI 在切换过程中可能会出现无响应的现象。