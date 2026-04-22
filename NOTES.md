# Playwright 心智模型笔记

README 是路线图（做什么），本文件是心智模型（怎么想）。每次回来前先扫一眼这里。

---

## 核心原则：定位器 × 动作 是两个独立维度

```
  定位器 (get_by_*)          动作 (.fill/.check/.click/...)
   "怎么找到元素"               "找到后干什么"
         ↓                            ↓
    page.get_by_label("E-mail").fill("...")
```

拿到定位器不会触发任何浏览器动作，它只是一个"查找描述"。必须接一个动作方法才有效果。

### Stage 1 亲身踩过的坑

```python
loc = page.get_by_role("button", name="Submit order")
# ← 到这里浏览器啥都没干。必须 .click()
```

**自检口诀**：写完一行 `get_by_*(...)` 问自己"接下来的动作呢？"

---

## 定位器三兄弟怎么选

| 元素类型 | 首选 | 原因 |
|---|---|---|
| 带 `<label>` 的表单字段（input / textarea / radio / checkbox） | `get_by_label("标签文字")` | 最贴近人类认知 |
| 按钮 / 链接 / 标题 | `get_by_role("button", name="按钮文字")` | 这些元素没 label，但有 ARIA role |
| 页面上的纯文本（欢迎语、错误提示） | `get_by_text("文字")` | 就是找文字 |
| 没 label 但有 placeholder 的搜索框 | `get_by_placeholder("...")` | 降级兜底 |

**为啥按钮不能用 `get_by_label`**：`<button>Submit order</button>` 里 "Submit order" 是按钮自己的文字，不是旁边的 `<label for="...">`。所以 label 查不到，必须用 role。

**先别学**：CSS selector、XPath。能语义定位就语义定位。

---

## 动作方法按元素类型匹配

```python
.fill("值")        # 文本类：input[type=text/email/tel/time]、textarea
.check()           # radio / checkbox
.uncheck()         # 取消勾选
.click()           # 任何可点元素
.select_option("值")  # <select> 下拉
```

`<input type="time">` 用 `.fill("18:30")` 就行，不需要特殊处理（已在 Stage 1 验证）。

---

## Python 函数签名读法

看 playwright 签名时经常有人懵。三个维度分开看：

```python
def get_by_role(
    self,
    role: Literal[...],          # 必传，可位置可 kwarg
    *,                           # ← 分水岭
    name: str | None = None,     # kwarg only，可省
    exact: bool | None = None,   # kwarg only，可省
    ...
) -> "Locator": ...
```

| 要判断什么 | 看什么 |
|---|---|
| 能不能省略 | 有 `= 默认值` 就可省 |
| 必须 kwarg 吗 | `*` 后面的参数必须 kwarg |
| 类型是啥 | 看 `:` 后面的标注（**和传参方式无关**） |

**容易混淆的点**：类型标注 (`role: Literal[...]`) 只说类型，不代表必须 kwarg 传。真正决定"必须 kwarg"的是签名里的 `*` 分水岭。

---

## 写法风格：链式 vs 变量暂存

❌ 每次 `loc = ...` 再调用：

```python
loc = page.get_by_label("Customer name")
loc.fill("李名言")
loc = page.get_by_label("Telephone")
loc.fill("13312345678")
```

✅ 链式更地道，读起来像人话：

```python
page.get_by_label("Customer name").fill("李名言")
page.get_by_label("Telephone").fill("13312345678")
```

**什么时候用变量暂存**：同一个定位器要多次用到（先 `.wait_for()` 再 `.click()`、或者先 `.screenshot()` 后面还要 `.click()`）。

---

## 表单提交后如何验收

浏览器跑完脚本不代表对，必须验证结果。Stage 1 学的几种方式：

```python
# 方式 1：截图人肉看
page.screenshot(path="submitted.png")

# 方式 2：打印跳转后页面内容
print(page.content())            # 整页 HTML
print(page.locator("pre").text_content())  # 只取 <pre> 里的内容

# 方式 3：等跳转完成后再断言
page.wait_for_url("**/post")

# 方式 4：调试神器——让浏览器别关，方便手动看
input("按回车关闭浏览器...")
```

Stage 1 成功标志：httpbin 返回的 JSON 里 `form` 对象有所有你填的字段，且 `Content-Type: application/x-www-form-urlencoded`（证明是真实表单提交，不是 JSON POST）。

---

## 网络层对照：httpx vs playwright

| 关注点 | httpx | playwright |
|---|---|---|
| 表单提交（form-urlencoded） | `client.post(url, data={...})` | `.fill()` + `.click()` 提交按钮 |
| JSON 提交 | `client.post(url, json={...})` | 一般不直接用，靠页面 JS 触发 |
| 忽略 TLS 证书 | `verify=False` | `new_context(ignore_https_errors=True)` |
| 复用 session | `AsyncClient` 实例 | `browser_context`（自动管 cookies） |
| 能跑 JS | ❌ 不能 | ✅ 真浏览器，JS 自动执行 |

**关键认知**：上一轮卡在 `flwq39` 加密字段上——那是 JS 生成的，httpx 不跑 JS 就算不出来。playwright 跑真浏览器，JS 自动执行，加密字段天然是对的。这就是我们转向 playwright 的根本原因。

---

## Stage 1 完整成果（供回顾）

脚本：`stage1_httpbin_form.py`

关键学到的：
1. `get_by_label` / `get_by_role` 搭配 `.fill` / `.check` / `.click` 能覆盖 90% 的表单操作
2. radio（Large）和 checkbox（Bacon）都用 `.check()`，区别在 HTML 语义
3. 只定位不动作 = 浏览器毫无反应（经典 bug）
4. 链式写法比变量暂存更像 playwright 风味
5. `input()` 是调试期让浏览器不自动关的土办法

---

## 下一站：Stage 2 预习

目标站：https://the-internet.herokuapp.com/login

关键新概念：
- **自动等待**（Playwright 比 selenium 爽的核心）：`.click()` / `.fill()` 自带"等元素出现+可交互"
- **显式等待**：`page.wait_for_url(...)`、`locator.wait_for(state="visible")`
- **断言**：`from playwright.sync_api import expect`，`expect(locator).to_be_visible()` 失败会自动重试一段时间再报错

**核心问题**（先自己想答案再查）：登录按钮点完后，怎么确认"已登录"？为啥不能用 `time.sleep(3)`？
