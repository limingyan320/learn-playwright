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

## Stage 2 新学的心智模型

### 1. 定位器到底走哪棵树

页面在浏览器里其实有**两棵树**：

```
DOM 树                         A11y Tree (Accessibility)
"HTML 结构本身"                 "屏幕阅读器看到的东西"
<button class="btn">Login</button>  →  {role: "button", name: "Login"}
<div>Welcome</div>                   →  {role: "text", name: "Welcome"} 或根本没进
```

定位器按走哪棵树分类：

| 定位器 | 走哪 |
|---|---|
| `get_by_role(...)` | **A11y Tree** |
| `get_by_label(...)` | DOM（找 `<label for="...">` 关联的 input） |
| `get_by_text(...)` | DOM（Text Node 的内容） |
| `get_by_placeholder(...)` | DOM（`placeholder` 属性） |
| `page.locator("#id .class")` | DOM（CSS selector） |

**一句话**：只要出现 `role` 字眼，你就在和 A11y Tree 打交道，其他都在 DOM 层。

**为什么 role 放最优先**：A11y Tree 是语义层，HTML 小改版通常不破坏 role/name，定位器天然抗样式/结构变化。

**HTML 到 role 的隐式映射**（浏览器自动推的）：

| HTML | 推导出的 role |
|---|---|
| `<button>` | `button` |
| `<a href="...">` | `link` |
| `<h1>`~`<h6>` | `heading` |
| `<input type="text">` | `textbox` |
| `<input type="checkbox">` | `checkbox` |
| `<div>` / `<span>` | **无**（只能靠 text/css 找） |

所以 div 包的纯文字只能用 `get_by_text`，这不是"降级"，是"对口"。

### 2. 自动等待 vs 显式等待

Playwright 的 `.click()` `.fill()` `.check()` 自带**可操作性等待**：

- 元素附加到 DOM
- 元素可见（visible）
- 元素稳定（不在移动）
- 元素能接收事件（没被覆盖）
- 元素启用（非 disabled）

五个条件都满足才会真的执行动作。**所以 90% 的场景不需要 `time.sleep()`**。

什么时候需要显式等待：

```python
# 等 URL 跳转完成（SPA 跳转、表单提交后跳转）
page.wait_for_url("**/secure")

# 等某个元素变成某个状态
locator.wait_for(state="visible")    # 默认
locator.wait_for(state="hidden")     # 等它消失（比如 loading 遮罩）
locator.wait_for(state="attached")   # 只要进 DOM 就行（不一定可见）

# 等某个 XHR 响应（Stage 3 会深入）
with page.expect_response(lambda r: "yzmQuery" in r.url) as info:
    page.click("查验")
```

**禁忌**：`time.sleep(3)`。要么太短（没等到）要么太长（浪费时间）。

### 3. 断言：声明，不是检查

```python
expect(page.get_by_text("You logged into a secure area!")).to_be_visible()
```

这行代码的含义**不是**"看看页面上有没有这句话"。含义是：

> "我**声明**：这里页面**必须**看到这句话。没看到就是 bug，停下报错。"

没有断言的脚本 = 盲打（exit 0 不等于功能对）。加了断言的脚本才是测试——exit 0 才真的意味着功能正确。

**expect 和 Python 原生 assert 的关系**：

| | `assert` | `expect()` |
|---|---|---|
| 本质 | 关键字/语句 | 函数，返回断言代理 |
| 行为 | 一次性判断 | **auto-retry**（默认 5s 内反复试） |
| 失败时抛 | `AssertionError` | `AssertionError`（同一个） |
| 可被 `-O` 禁用 | 可以 | 不可以 |

共通点只有"失败时都抛 AssertionError"。不是继承关系，是巧合。

### 4. 一场景一测试（失败场景的写法）

herokuapp 登录失败有两种提示：用户名错 → "Your username is invalid!"，密码错 → "Your password is invalid!"。

**反模式**——一个脚本里自适应判断：

```python
# ❌
if "username" in page.content():
    expect(page.get_by_text("username is invalid")).to_be_visible()
else:
    expect(page.get_by_text("password is invalid")).to_be_visible()
```

这样测试在"迎合现实"，永远不会失败，失去意义。

**正确做法**——每个场景独立一份脚本：

- `stage2_bad_username.py`：故意输错用户名，断用户名错
- `stage2_bad_password.py`：故意输错密码，断密码错

**口诀**：测试不问"现在什么情况"，测试问"该是什么情况"。固定输入 + 固定期望 = 可信测试。

### 5. `input()` 撑着浏览器的机制

```python
with sync_playwright() as p:
    ...
    expect(...).to_be_visible()   # 通过就沉默
    input("\n")                    # 卡住主进程
```

Playwright 的 Chromium 是 Python 的**子进程**，Python 主进程在 `input()` 卡着 = 子进程跟着活 = 浏览器不关。敲回车 → `input()` 返回 → `with` 块退出 → `__exit__` 关浏览器。

想让**失败时也能留现场**：

```python
try:
    expect(...).to_be_visible()
finally:
    input("回车关闭...")    # 无论成败都挂起
```

`finally` 保证无论 try 块正常 return 还是异常抛出都会执行，和 `with` 的 `__exit__` 是同一套哲学。

---

## Stage 2 完整成果（供回顾）

脚本：
- `stage2_success_herokuapp.py` — 正确凭据 → 断言 "You logged into a secure area!" 可见
- `stage2_bad_username.py` — 错误用户名 → 断言 "Your username is invalid!" 可见
- `stage2_bad_password.py` — 错误密码 → 断言 "Your password is invalid!" 可见

关键学到的：

1. A11y Tree 和 DOM 是两棵树，`get_by_role` 走前者，其他都走后者
2. `.click()` / `.fill()` 自带等元素可操作，不用 `sleep`；跳转等待用 `wait_for_url`
3. 断言是**声明期望**，不是检查现状；失败场景一场景一测试，不要 if/else 自适应
4. `expect` 的 auto-retry 是它比 `assert` 强的地方（页面 async 更新也能等到）
5. `input()` 卡主进程 = 保活浏览器；想"失败时留现场"用 `try/finally`

---

## 下一站：Stage 3 预习

**目标**：不靠 parse DOM 拿结果，直接**拦网络响应**。这一步直接对准最终的税务核验——它的结果是 JSONP 返回，拦响应比读 DOM 更稳。

关键 API：

```python
# 1. 被动监听（事件驱动）
page.on("request", lambda r: print(r.url))
page.on("response", lambda r: print(r.status, r.url))

# 2. 主动等（block 到某个响应出现）
with page.expect_response(lambda r: "yzmQuery" in r.url) as info:
    page.click("查验按钮")
resp = info.value
print(resp.json())   # 或 .text() / .body()

# 3. 甚至拦截修改（mock 响应，高级用法）
page.route("**/api/**", lambda route: route.fulfill(json={"fake": "data"}))
```

**核心问题**（先自己想答案再查）：

1. `page.on("response", ...)` 和 `page.expect_response(...)` 这俩 API 区别在哪？什么时候用哪个？
2. 为啥说"拦 XHR 响应比 parse DOM 更可靠"？
