# AKTools MCP

这是项目内第二个免费数据源接入层。

- `AKTools HTTP`：本地 Python 服务，负责暴露 AKShare 数据接口
- `aktools MCP`：项目内 MCP 封装，负责让 Codex 直接调用 AKTools 接口

## 结构

- `server.mjs`：Codex MCP 封装
- `start-aktools.ps1`：启动本地 AKTools HTTP 服务
- `install-codex-config.ps1`：把 `aktoolsMcp` 写入 `C:\Users\Administrator\.codex\config.toml`

## 依赖

需要先安装 Python 3.10+，然后安装 AKTools：

```powershell
python -m pip install -U aktools
```

如果你的系统里还没有 Python，先装 Python，再重新打开 PowerShell。

## 启动 AKTools HTTP

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\股票分析\mcp\aktools\start-aktools.ps1"
```

默认监听：

- `http://127.0.0.1:8080`

Swagger 文档：

- `http://127.0.0.1:8080/docs`

OpenAPI：

- `http://127.0.0.1:8080/openapi.json`

## 写入 Codex 配置

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\股票分析\mcp\aktools\install-codex-config.ps1"
```

脚本会写入：

- MCP 服务名：`aktoolsMcp`
- 默认 `AKTOOLS_BASE_URL`：`http://127.0.0.1:8080`

写完之后，重启 Codex 或新开线程，让新工具加载进来。

## 提供的 MCP 工具

- `aktools_health`
- `aktools_openapi`
- `aktools_public_endpoint`
- `aktools_stock_zh_a_hist`
- `aktools_stock_comment_em`
- `aktools_docs`

## 推荐用途

- A 股免费历史数据
- 用 OpenAPI 动态发现 AKShare 可用函数
- 作为东方财富 MCP 之外的第二数据源做交叉校验

## 注意

- AKTools 本质上是 AKShare 的 HTTP 封装，接口稳定性取决于上游站点。
- 免费源适合研究和日常跟踪，不适合高频或严肃交易基础设施。
