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

## Stage 3 新学的心智模型

### 1. 网页内容变化的三种模式

| 模式 | 例子 | 提交后发生什么 | 数据怎么拿 |
|---|---|---|---|
| 传统表单 | Stage 1 httpbin、Stage 2 herokuapp | 整页刷新，URL 跳转 | parse 新页面 DOM |
| AJAX 局部更新 | 淘宝搜索建议、税务查验 | URL 不变，JS 局部塞数据 | **拦网络响应**（推荐）或 parse DOM |
| SPA 单页应用 | 现代 React/Vue 站 | 整站全靠 AJAX，URL 用 hash/history 假装变 | 同上 |

判断口诀：操作完 URL 变没变？变了 = 传统模式；没变但有新内容 = AJAX。

### 2. AJAX 名词体系：一次记死

```
AJAX       ← 设计模式（"局部刷页"），不是 API
  ├── XHR (XMLHttpRequest)  ← 1999 年微软的老 API
  ├── Fetch                 ← 2015 年标准化的现代 API
  └── JSONP                 ← <script> 标签 hack，绕跨域用，老政府/老银行还在用
```

**JSONP** = **JSON** with **P**adding。"Padding" 指外面那层函数调用包装：

```
jQuery361074(...{真JSON}...)
└─────┬─────┘└─────┬─────┘└┘
   前壳         真JSON     后壳
```

为啥 padding？JSON 单独 `{...}` 不是合法 JS 语句（被当成块作用域），包成 `func({...})` 才是合法函数调用，浏览器加载这个 .js 文件时会真去**调用** `func`，把 JSON 当参数传进去 —— 借 `<script>` 标签不受同源策略限制的特性偷数据。

**辨认 JSONP**：

- URL 含 `?callback=xxx` 或 `?cb=xxx`
- Response Content-Type = `text/javascript` 或 `application/javascript`
- Response 体形如 `funcname({...})`
- HTTP 方法**只能是 GET**（`<script src>` 限制）

### 3. Network 面板里的两类请求

> Network 面板里的每一条 = "**当前这个标签页**内浏览器**到任意服务器**发出的一次 HTTP 请求"。

| 类别 | 例子 | 触发源 |
|---|---|---|
| 资源请求 | HTML / CSS / JS / 图片 / 字体 / favicon | 浏览器自动 —— 解析 HTML 看到 `<link>` `<script>` `<img>` 就自己去 GET |
| 业务请求（AJAX） | vatQuery / yzmQuery / 各种 API | JS 触发 —— 用户点了按钮，绑定的 onClick 跑起来发 fetch/XHR/script |

**关键认知**：HTTP 请求 ≠ "API 调用"。**Web 上你看到的每一个字节都是浏览器一个个 HTTP GET 拉回来的**。一个普通页面常常一开就是 50~100 条请求，绝大多数都是资源拉取。

### 4. Network 面板读法（避免被字段坑）

| 信息 | 在哪看 | 注意 |
|---|---|---|
| 真正的请求方法 | General → Request Method | **这是真相** |
| 服务器允许的跨域方法 | Response Headers → Access-Control-Allow-Methods | **CORS 元数据**，跟单次请求方法无关 |
| 响应内容类型 | Response Headers → Content-Type | JSONP 的招牌：`text/javascript` |
| 响应体（原始） | Response 标签 | 一字不改 |
| 响应体（美化） | Preview 标签 | JSON 折叠树、图片直接显示、JSONP 不会自动美化 |
| 哪段 JS 触发的请求 | Initiator 标签 | 调试 AJAX 来源很有用 |

`data:image/png;base64,...` **严格说不是网络请求**，是 HTML 内联的图片，浏览器本地解码 base64 就显示了。Network 面板列它是为了完整性。

### 5. Playwright 不发请求，只窃听浏览器

最大心智误区：**以为 Playwright 是"帮我发请求的工具"**。错。

正确模型：

```
Python 进程                       浏览器进程（Chromium）
   │                                      │
   │ p.chromium.launch()              ┌───↓───┐
   │ ────────启动────────────────────→│       │
   │ page.click("按钮")                │       │
   │ ────────遥控指令───────────────→│       │
   │                                  │  JS   │ ← onClick 触发
   │                                  │       │ ← 自己算 flwq39
   │                                  │       │ ← 自己拼 URL
   │                                  │       │ ← 自己发 fetch/script
   │                                  │       │
   │      ┌─────响应到达浏览器───────┤       │
   │ ←────expect_response 截下─────┤       │
   │                                  └───────┘
   └──────────（两进程不共享网络栈）──────────
```

**两个进程独立**：Python 里 `httpx.get(...)` 直连服务器，**Playwright 完全看不见**（不在浏览器进程里）。这就是为啥上一轮 httpx 卡死换 Playwright 能解决 —— 真浏览器自己跑 JS 算 flwq39 + 维护 session，我们只要触发 + 截响应。

**Playwright 的护城河**（Stage 3 亲眼证实）：

1. 前端混淆 JS 算的加密字段（flwq39）—— 浏览器自己跑
2. session 状态、cookies、anti-replay 标记 —— 浏览器自己维护

curl 一字不差复制浏览器 URL 也会失败 —— 不是 URL 错，是上下文丢了。

### 6. expect_response vs page.on

| | `page.on("response", handler)` | `page.expect_response(predicate)` |
|---|---|---|
| 模式 | 被动订阅，广播 | 主动等待，单条 |
| 触发时机 | 每条响应都喂给 handler | block 主流程到匹配响应到达 |
| 拿响应 | handler 副作用（打印/存列表） | `info.value` 直接同步取 |
| 适用场景 | 调试日志、监控 | **触发动作 + 拿结果**（99% 工程用这个） |

生产里 `expect_response` 占绝对主导。`page.on` 适合学习时观察，工程上很少单独用。

### 7. Predicate 这个词，以及 lambda 速成

**Predicate = 谓词**，来自逻辑学：**返回 True/False 的判断函数**，不是"动词"。

```
P(x)   ← 谓词函数 P 应用于参数 x，返回真假
IsHuman(苏格拉底) → True
GreaterThan100(99) → False
```

中文别被"谓词"两字误导，理解成"判断函数"或"过滤函数"更直观。

**Lambda = 匿名函数**，写法：

```python
lambda <参数>: <一个表达式（自动 return）>

# 等价于
def 这个东西没名字(<参数>):
    return <一个表达式>
```

JS 箭头函数 `r => r.url.includes("json")` 同思想。Python lambda 限制更狠：**只能一个表达式**，不能多行/不能 if/不能 return。复杂逻辑必须用 def。

**Predicate 配 lambda 的标准 idiom**：

```python
page.expect_response(lambda r: "vatQuery" in r.url)
```

精度调节（太低误匹配，太高漏匹配）：

```python
lambda r: "vatQuery" in r.url and r.status == 200    # 加 status 过滤掉 OPTIONS 预检
lambda r: r.url.endswith("/vatQuery")                  # 路径精确
```

### 8. with 块 + info.value 的执行顺序（必须想通）

```python
with page.expect_response(lambda r: "vatQuery" in r.url) as info:
    # ① 进入 with：监听器立刻装好
    page.click("查验按钮")
    # ② 触发动作：浏览器开始处理
# ③ 离开 with：BLOCK 等匹配的响应到达，超时（默认 30s）抛 TimeoutError

response = info.value    # ④ 出 with 块后才有值，块内时 info 还是空的
print(response.json())
```

关键：**监听器必须在动作之前装好**。如果先 click 再 listen，响应可能比 listener 注册更快到达，被错过。

### 9. Response 对象的三种读取方式

| 方法/属性 | 加括号? | 拿啥 | 何时用 |
|---|---|---|---|
| `.url` | 否 | str | URL（属性） |
| `.status` | 否 | int | HTTP 状态码（属性） |
| `.headers` | 否 | dict | 响应头（属性） |
| `.text()` | 是 | str | **任何文本**（HTML/XML/JSONP/普通文本） |
| `.json()` | 是 | dict | 严格 JSON 自动 parse；**JSONP 用会爆** |
| `.body()` | 是 | bytes | 二进制（图片、PDF）或自己挑编码（如 GBK） |

**JSONP 必须用 `.text()`**，自己剥外壳后再 `json.loads()` 或 `json5.loads()`。

### 10. 触发 AJAX 的两种姿势：fetch 撞 CORS vs script 注入

历史的讽刺：**JSONP 这个东西诞生的全部意义就是为了绕开 CORS**。然后用 fetch（受 CORS 管的现代 API）去调 JSONP（专门躲 CORS 的老 hack）—— 必然撞墙。

| 触发方式 | CORS | 适用 |
|---|---|---|
| `fetch('...')` | ✅ 受 CORS 管 —— 服务器没设 `Access-Control-Allow-Origin` 就拦死 | 标准 JSON / 同源 / CORS 友好的 API |
| 注入 `<script src>` | ❌ 不管 —— `<script>` 标签历史上一直能跨域 | **JSONP 专用** |

**Script 注入模板**：

```python
page.evaluate("""
    const s = document.createElement('script');
    s.src = 'https://suggestion.baidu.com/su?wd=python&cb=myCb';
    document.head.appendChild(s);
""")
```

把 `<script>` 元素塞进 `<head>` 的瞬间，浏览器自动 GET 那个 URL。Playwright `expect_response` 一样能截到（**网络层不在意 JS 用啥 API 触发**）。

记忆：CORS 只拦"JS 读响应"，不拦请求本身。所以 fetch 报 "Failed to fetch"（JS 读不到），但网络请求其实发出去了 —— 不过对你**消费数据**这件事没用，所以还是得换 script。

### 11. 严格 JSON vs JS 对象字面量

JSON 是 JS 对象语法的**严格子集**。野生 JSONP 接口经常返回的是 JS 对象字面量，不是合法 JSON：

| 特性 | JS 对象字面量 | 严格 JSON |
|---|---|---|
| 键不加引号 `{q:"x"}` | ✅ | ❌ |
| 字符串单引号 `{"q":'x'}` | ✅ | ❌（必须双引号） |
| 尾随逗号 `[1,2,]` | ✅ | ❌ |
| 注释 | ✅ | ❌ |

**对应 Python parse 选择**：

| 接口 | 内层格式 | 用啥 |
|---|---|---|
| 百度 suggest | JS 对象字面量（键无引号） | `json5.loads()` |
| 税务 vatQuery | 严格 JSON | `json.loads()` |

`json5` 是 JSON 的扩展，容忍所有 JS 字面量松散写法，API 与 `json` 一致（`loads` / `dumps`）。

### 12. Regex 剥 JSONP 外壳 + Pyright 类型收窄

**通用 JSONP 剥壳模板**：

```python
import re
match = re.match(r'^\s*\w+\((.*)\);?\s*$', raw, re.DOTALL)
if match is None:
    raise RuntimeError(f"剥壳失败: {raw!r}")
inside = match.group(1)
```

正则各部分：

| 片段 | 匹配 |
|---|---|
| `^\s*` | 开头 + 任意空白 |
| `\w+` | 回调函数名（字母/数字/下划线） |
| `\(` | 字面量左括号（转义） |
| `(.*)` | **捕获组**：贪婪匹配中间所有内容 → `match.group(1)` |
| `\)` | 字面量右括号 |
| `;?\s*$` | 可选分号 + 可选空白 + 结尾 |

`re.DOTALL` 标志：让 `.` 匹配换行符。响应跨多行必须开。

`re.match` 返回 `Match | None`：**失败返回 `None`，不是空字符串**。直接 `.group(1)` 会 `AttributeError`。

**Pyright 类型收窄**：

```python
match = re.match(...)            # 类型: Match[str] | None
if match is None:                # ↓
    raise ...                    # 这条路退出
inside = match.group(1)          # Pyright 收窄为 Match[str]，警告消失
```

`if x is None: raise ...` 之后，Pyright 自动推断后续 x 不可能是 None，类型自动变窄。这是现代类型检查器最有用的特性之一。

### 13. is None vs == None

```python
if match is None:    # ✅ PEP 8 标准
if match == None:    # ⚠️ 不推荐
```

`None` / `True` / `False` 是单例对象。用 `is`（指针比较）：

- 更快（指针比较 vs 调用 `__eq__`）
- 更可靠（不会被某个类的 `__eq__` 重写骗到）
- PEP 8 / linter (E711) 强制要求

习惯：**只要比的是 None/True/False，永远用 `is`**。

---

## Stage 3 完整成果（供回顾）

脚本：

- `stage3_intercept.py` — `expect_response` + `page.evaluate("fetch(...)")` 拦下 httpbin.org/json 的标准 JSON 响应，打印 status/url/.json()
- `stage3_jsonp.py` — `<script>` 注入触发百度 suggest，regex 剥 JSONP 外壳，json5 parse JS 对象字面量

关键学到的：

1. AJAX/JSONP 是历史化石，但税务总局还在用，绕不开
2. Playwright 不发请求，只在网络层窃听浏览器自己发的请求
3. expect_response = with 块 + as info + .value 这套 idiom
4. JSONP 必须 `<script>` 注入，不能 fetch（CORS）
5. JSONP 解析两步走：regex 剥壳 + json/json5 parse
6. 严格 JSON 用 json，野生 JS 字面量用 json5
7. `re.match` 必须判 None，否则崩；Pyright 帮你提前发现

---

## 下一站：Stage 4 预习

**目标**：把 Stage 0–3 所有技能合在一起，攻打真正的税务总局查验页。

**新概念**（不多）：

```python
# 1. 容忍自家 CA 的 TLS（税务总局必备）
context = browser.new_context(ignore_https_errors=True)
page = context.new_page()

# 2. 元素截图（可选，给 Stage 5 OCR 用）
page.locator("img.captcha").screenshot(path="captcha.png")

# 3. 长发票号拆分
fphm_full = "25377000000496974821"   # 20 位
fpdm = fphm_full[:12]                  # 253770000004
fphm = fphm_full[12:]                  # 96974821
```

**核心问题**（先想答案再写）：

1. 拦 vatQuery 响应时，predicate 应该匹配啥关键字最稳？想想**只有 vatQuery 才独有**的 URL 特征。
2. 假设你点了"获取验证码"按钮后，要等到验证码图片**真的出现**再继续下一步。怎么写显式等待？回想 Stage 2 的 `wait_for` / `expect`。
3. 验证码图片是 `<img src="data:image/png;base64,xxxxxxx">` —— 你想拿到那张图（图片字节、不是 src 整个字符串），有几条路？提示：DOM 提取 vs 拦 yzmQuery 响应。

把 Stage 3 学到的东西原封不动用上去，加一点 UI 交互层的粘合，就是 Stage 4。
