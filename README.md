# Playwright 学习路线：复现政府核验接口

这个仓库是我为了学 Playwright 开的沙盒。最终目标是**手写一个 FastAPI 服务，用 Playwright 驱动浏览器去国家税务总局发票查验平台自动查验发票**，部署到 ai-dev，给内网无外网的星火系统调用。

不让 agent 代写代码，只让它当老师。遇到的每一个坑都要自己栽一遍。

---

## 最终成果验收标准

一个 `/api/gov-verify` 接口，接收：

```json
{
  "fphm": "25377000000496974821",
  "kprq": "20251024",
  "je": "24.00"
}
```

内部流程：

1. 用 Playwright 打开 `https://inv-veri.chinatax.gov.cn/` （或对应省份的查验页）
2. 填入发票号码、开票日期、金额
3. 截取验证码图片，过 OCR（ddddocr）识别
4. 点提交，拿到查验结果
5. 解析成结构化 JSON 返回

部署在 ai-dev（192.168.100.30），前面挂 Caddy 反向代理。

---

## 为什么选 Playwright 而不是 httpx

上一轮用 httpx 硬刚，卡在两个地方：

1. **TLS**：税务总局用的是自家的"税务电子证书管理中心"CA，不在公共信任库里。httpx 可以 `verify=False` 绕过，但 Chrome 浏览器默认会拦死（除非 `--ignore-certificate-errors`）
2. **JS 加密字段 `flwq39`**：查验请求的 query string 里有一个 236 字符的 base64 加密串，里面藏了 `kprq` 和验证码答案 `jym`，由前端压缩过的 JS（version `v=2.0.23_090`）生成。想 httpx 直连就得逆向这段 JS——SM2/AES 都有可能，工程量大且不稳定

Playwright 跑的是真浏览器，JS 自动执行，`flwq39` 自然就算好了。我们只负责"人类会做的事"：填表、识别验证码、点按钮。

代价：慢（浏览器启动开销）、重（~170MB Chromium）、有状态（cookies/session）。但对这种低 QPS 的查验接口够用。

---

## 学习路线

每个 stage 有**明确的验收物**。前一个不过不做下一个。

### Stage 0：Hello Playwright ✅

**验收物**：`hello_playwright.py` 跑完产出 `hello.png`，截图里能看到真实的网页（不是空白）

**学到了**：
- `uv add playwright` 装的是 Python 驱动代码
- `uv run playwright install chromium` 装的是 ~170MB 的浏览器二进制（两步都不能少）
- `sync_playwright()` 上下文管理器、`chromium.launch(headless=...)`、`browser.new_page()`、`page.goto(...)`、`page.screenshot(path=...)`

**踩过的坑**：
- nvim pyright 报 `Import "playwright.sync_api" could not be resolved`，但 `uv run python hello_playwright.py` 能跑。原因：pyright 默认用系统 Python，没看到 `.venv/`。在项目根写 `pyrightconfig.json`：
  ```json
  {"venvPath": ".", "venv": ".venv"}
  ```
  然后 `:LspRestart`

---

### Stage 1：httpbin 表单填写

**目标网址**：https://httpbin.org/forms/post （一个真实的 HTML 披萨订单表单）

**验收物**：写一个脚本，自动填完所有字段（customer name、phone、email、pizza size、toppings 多选、delivery time、comments），点 submit，把返回的 JSON 打印出来，且打印的内容里有你填的值

**要学的概念**：

定位器三件套（优先级从高到低，越靠上越稳定）：
- `page.get_by_role("textbox", name="Customer name")` — 无障碍树定位
- `page.get_by_label("Customer name")` — 用 `<label>` 文本定位
- `page.get_by_placeholder("...")` — 用占位符定位

动作方法：
- `.fill("文本")` — 清空并填入文本框
- `.check()` / `.uncheck()` — 复选框
- `.click()` — 点击
- `.select_option("值")` 或 `.select_option(label="...")` — 下拉

提交后页面会跳转到 `/post`（JSON 回显），用 `page.content()` 或 `page.locator("pre").text_content()` 读出来。

**先别学**：CSS selector、XPath。能用语义定位就用语义。

---

### Stage 2：带等待的登录流程

**目标网址**：https://the-internet.herokuapp.com/login （一个专门给爬虫练手的站）

**验收物**：账号 `tomsmith` / 密码 `SuperSecretPassword!` 登录成功，跳到 `/secure` 页面后断言"You logged into a secure area!"这个横幅出现，截图保存；再测一遍错误密码，断言看到错误提示

**要学的概念**：
- **自动等待**：Playwright 的 `.click()` `.fill()` 自带"等元素出现+可交互"的等待，不需要手写 `sleep`。这是它比 selenium 爽的核心原因之一
- **显式等待**：`page.wait_for_url("**/secure")`、`page.wait_for_selector(...)`、`locator.wait_for(state="visible")`
- **断言**：`from playwright.sync_api import expect`；`expect(locator).to_be_visible()`、`expect(locator).to_have_text("...")`。断言失败会自动重试一段时间再报错
- **上下文隔离**：`browser.new_context()` vs 复用 page。不同测试之间用 new_context 避免 cookie 污染

**关键问题**：登录按钮点完之后，什么时候才能确认"已经登录了"？不要用 `sleep(3)`，要用 `wait_for_url` 或 `expect` 某个只有登录后才出现的元素。

---

### Stage 3：拦截 XHR 响应

**目标网址**：任选一个会发 AJAX 请求的页面，比如 https://httpbin.org/ 上自己用 `fetch()` 发个请求，或者 https://jsonplaceholder.typicode.com/

**验收物**：脚本触发一次 AJAX，在浏览器发出去之前就把响应体捕获下来并打印

**要学的概念**：
- `page.on("request", handler)` / `page.on("response", handler)` — 订阅所有网络事件
- `page.wait_for_response(lambda r: "yzmQuery" in r.url)` — 等某一个特定响应，返回 Response 对象
- `await response.json()` / `response.text()` / `response.body()` — 读内容
- `page.route("**/api/**", handler)` — 甚至可以拦截改请求/伪造响应（mock）

**为什么这步重要**：税务总局的查验结果是 JSONP 回调，页面上**可能不直接显示完整结构化数据**，但网络响应里有。我们很可能不是去 parse DOM，而是直接拦截查验响应。

---

### Stage 4：真实目标——税务查验页

**目标网址**：https://inv-veri.chinatax.gov.cn/ （或走具体省份，比如 https://fpcy.shandong.chinatax.gov.cn/）

**验收物**：脚本自动把一张真实发票的字段填进去，**手动输入验证码**（这一关先不搞 OCR），提交后能看到查验结果页或拦到查验响应。用的发票先用上一轮那张：
- fphm: 25377000000496974821（全电票号码，20 位，前 12 位是 fpdm=253770000004，后 8 位是 fphm=96974821）
- kprq: 20251024
- je: 24.00

**新学的概念**：
- **上下文配置**：`browser.new_context(ignore_https_errors=True)` —— 对应 httpx 的 `verify=False`
- **元素截图**：`locator.screenshot(path="captcha.png")` —— 只截一个元素（验证码 `<img>`），不是整页
- **输入中文**：`.fill("中文")` 一般就行，但如果是富文本/特殊组件可能要 `.type("中文", delay=100)` 模拟按键
- **人类行为伪装**：User-Agent（`new_context(user_agent=...)`）、`slow_mo`、`page.mouse.move(...)` 不规则鼠标移动

**踩坑预警**：
- 两个域名（`inv-veri.*` 和 `fpcy.shandong.*`）都用内部 CA，都需要 `ignore_https_errors`
- 新版全电票发票号码是 20 位，查验页的表单字段通常分成 `发票代码(12)` + `发票号码(8)`，要自己拆
- 验证码 `<img>` 的 `src` 可能是 `data:image/png;base64,...`（base64 内联），也可能是单独 URL，两种情况都要能处理

---

### Stage 5：OCR + 重试

**验收物**：Stage 4 的脚本去掉"手动输入验证码"，改成自动识别。识别错了能自动换一张重试，最多试 N 次。

**要学的内容**：
- `ddddocr`：国产验证码 OCR 库，`pip install ddddocr`。对 4 字中文常规验证码识别率 ~60-80%
  ```python
  import ddddocr
  ocr = ddddocr.DdddOcr()
  result = ocr.classification(image_bytes)
  ```
- **刷新验证码**：一般是点那张 img 自己，或者有个"看不清换一张"链接
- **重试骨架**：
  ```
  for attempt in range(5):
      截验证码 → OCR → 填 → 提交
      if 查验响应.success:
          break
      else:
          刷新验证码
  ```
- **失败原因分类**：验证码错 vs 票据信息错 vs 被风控。上一轮的经验：风控后会要求长时间冷静期，不要盲目重试

---

### Stage 6：封装成 FastAPI + 部署

**验收物**：
1. ai-dev 上 `/home/limingyan/gov-verify/main.py` 里有 `/api/gov-verify` 端点
2. Caddy 反向代理挂上去，内网 curl `http://<caddy-domain>/api/gov-verify` 能拿到结构化 JSON
3. 并发至少扛住 2（Playwright browser 实例复用或池化）

**要学的内容**：
- **async playwright**：FastAPI 是 async 的，生产上用 `from playwright.async_api import async_playwright`，不是 `sync_api`。API 基本一致，所有 IO 加 `await`
- **浏览器生命周期**：不要每次请求都启动 Chromium（慢）。在 FastAPI `lifespan` 里启一次 browser，每次请求 `browser.new_context()`（轻量）
- **无头**：服务器没显示器，必须 `headless=True`
- **超时与清理**：单次查验设 30s 上限，失败/超时强制关 context 防内存泄漏
- **并发控制**：`asyncio.Semaphore(2)` 限制同时跑的 context 数，防止税务网站风控
- **日志**：每一步截图存到临时目录，出错时留证据

**部署要点**（对照 `receipt-judge` 的 CLAUDE.md 成熟范式）：
- 本机写代码 → git push → ssh ai-dev git pull → 重启服务
- 浏览器二进制装在 ai-dev 上：`uv run playwright install chromium --with-deps`
- systemd 或 `setsid nohup` 起服务

---

## 参考资料

- Playwright Python 官方文档：https://playwright.dev/python/docs/intro
- 定位器最佳实践：https://playwright.dev/python/docs/best-practices
- ddddocr 项目：https://github.com/sml2h3/ddddocr
- 上一轮探索的脚本（对照参考，不要直接抄）：`/Users/lumynous/receipt-judge/scripts/gov_verify_probe.mjs` —— Codex 写的 Node 版 probe，里面 `ignoreHTTPSErrors: true` 的用法可以印证我们的判断

## 当前进度

- [x] Stage 0：hello_playwright.py
- [x] Stage 1：httpbin 表单（stage1_httpbin_form.py）
- [x] Stage 2：登录 + 等待（stage2_success_herokuapp.py / stage2_bad_username.py / stage2_bad_password.py）
- [ ] Stage 3：XHR 拦截
- [ ] Stage 4：税务查验页（手动验证码）
- [ ] Stage 5：OCR + 重试
- [ ] Stage 6：FastAPI + 部署
