# nonebot-plugin-nc-status

<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

[![NoneBot](https://img.shields.io/badge/NoneBot-2.0+-red.svg)](https://nonebot.dev/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**NoneBot2 专用的 NapCat 状态监控插件**

</div>

---

## 📖 简介

`nonebot-plugin-nc-status` 是一个用于监控多个 NapCat（或其他 OneBot 实现）实例运行状态的 NoneBot2 插件。

插件会按照设定的时间间隔（默认 30 秒）自动轮询所有配置的连接地址，检测各个 Bot 实例的在线状态。当某个实例连续多次（默认 6 次）检测异常时，会自动向指定群聊发送掉线警报。

## ✨ 功能特性

- 🔄 **自动轮询** - 定时检测所有配置的 Bot 实例状态
- 📊 **多实例支持** - 支持同时监控多个 NapCat/OneBot 实例
- 🚨 **智能告警** - 连续多次异常才触发告警，避免误报
- 🔌 **长连接复用** - 使用 httpx 异步客户端，高效复用连接
- 📝 **手动查询** - 支持通过指令手动查询当前状态
- ⚙️ **灵活配置** - 所有参数均可通过配置文件自定义

## 🔧 安装

### 依赖要求

- Python 3.10+
- NoneBot2 2.0+
- OneBot V11 适配器

---

### 📌 推荐安装方式（全新环境）

建议使用独立的虚拟环境安装，避免与其他项目产生依赖冲突。

#### 1. 创建项目目录并进入

```bash
mkdir nonebot-nc-status
cd nonebot-nc-status
```

#### 2. 创建并激活虚拟环境

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（Windows PowerShell）
.\.venv\Scripts\Activate.ps1

# 激活虚拟环境（Windows CMD）
.\.venv\Scripts\activate.bat

# 激活虚拟环境（Linux/macOS）
source .venv/bin/activate
```

#### 3. 安装 NoneBot2 脚手架

```bash
pip install nb-cli
```

#### 4. 创建 NoneBot2 项目

```bash
nb create
```

按照提示选择：

- 项目名称：自定义
- 驱动器：`FastAPI`（推荐）
- 适配器：`OneBot V11`

#### 5. 安装插件依赖

```bash
# 进入项目目录（如果不在的话）
cd nonebot-nc-status

# 使用本项目提供的 requirements.txt 安装所有依赖
pip install -r requirements.txt
```

或者手动安装：

```bash
# NoneBot2 核心（nb create 已安装）
pip install nonebot2
nb driver install nonebot2[fastapi]
nb adapter install nonebot-adapter-onebot

# 必需插件
pip install nonebot-plugin-apscheduler
pip install nonebot-plugin-htmlrender

# HTTP 客户端
pip install httpx

# TOML 解析（Python 3.10 需要，3.11+ 已内置）
pip install tomli
```

#### 6. 安装本插件

将插件文件夹 `nc_status` 复制到项目的 `src/plugins/` 目录下：

```
your-project-name/
├── src/
│   └── plugins/
│       └── nc_status/        ← 放这里
│           ├── __init__.py
│           ├── config.py
│           └── connections.toml（首次启动自动生成）
├── .venv/
├── pyproject.toml
└── ...
```

#### 7. 启动 Bot

```bash
nb run
```

---

### 🔄 快速安装方式（已有项目）

如果你已有 NoneBot2 项目，可以直接安装依赖：

```bash
# 安装依赖插件
pip install nonebot-plugin-apscheduler nonebot-plugin-htmlrender httpx

# Python 3.10 还需要安装 tomli
pip install tomli
```

然后将 `nc_status` 文件夹复制到 `src/plugins/` 目录下即可。

---

### 加载插件

插件放到 `src/plugins/` 目录后会自动加载。

如需手动指定，在 `pyproject.toml` 中添加：

```toml
[tool.nonebot]
plugins = ["nc_status"]
```

## ⚙️ 配置

首次启动时，插件会自动在插件目录下生成 `connections.toml` 配置文件。

### 配置文件示例

```toml
[settings]
interval = 30           # 轮询间隔（秒）
timeout = 10            # 请求超时（秒）
group = 123456789       # 上报群号（收到告警的群）
error_threshold = 6     # 连续错误阈值（达到后才上报）
retry_count = 3         # 重试次数（暂未使用）

# 连接配置 - 每个 [[connections]] 块代表一个监控目标
[[connections]]
name = "主Bot"          # 连接名称（用于识别）
host = "127.0.0.1"      # NapCat 地址
port = 3000             # NapCat HTTP 端口
token = "your_token"    # 访问令牌（与 NapCat 配置一致）

[[connections]]
name = "备用Bot"
host = "127.0.0.1"
port = 3001
token = "another_token"
```

### 配置说明

| 参数                | 类型 | 默认值 | 说明                         |
| ------------------- | ---- | ------ | ---------------------------- |
| `interval`        | int  | 30     | 状态检测间隔（秒）           |
| `timeout`         | int  | 10     | HTTP 请求超时时间（秒）      |
| `group`           | int  | -      | 告警消息发送的目标群号       |
| `error_threshold` | int  | 6      | 连续检测失败多少次后触发告警 |
| `name`            | str  | -      | 连接的显示名称               |
| `host`            | str  | -      | NapCat 实例的 IP 地址        |
| `port`            | int  | -      | NapCat 实例的 HTTP API 端口  |
| `token`           | str  | -      | NapCat 的 Access Token       |

## 📋 指令

| 指令          | 权限      | 说明                   |
| ------------- | --------- | ---------------------- |
| `nc状态`    | SUPERUSER | 查询当前所有实例的状态 |
| `nc status` | SUPERUSER | 同上（英文别名）       |

### 错误类型说明

| 类型           | 说明            | 可能原因                          |
| -------------- | --------------- | --------------------------------- |
| `offline`    | 连接失败        | NapCat 未启动、端口错误、网络不通 |
| `http_error` | HTTP 状态码异常 | 服务内部错误、认证失败            |
| `bot_error`  | 业务状态异常    | Bot 账号异常、协议问题            |

## 📁 文件结构

```
nonebot-plugin-nc-status/
├── __init__.py          # 插件主文件
├── config.py            # 配置加载模块
├── connections.toml     # 配置文件（首次启动自动生成）
└── README.md            # 说明文档
```

## ⚠️ 注意事项

1. **首次启动**：插件会自动生成默认配置文件，请修改后重新启动
2. **Token 配置**：确保 `token` 与 NapCat 配置的 `accessToken` 一致
3. **端口配置**：使用 NapCat 的 HTTP 服务端口，不是 WebSocket 端口
4. **群号配置**：确保 Bot 已加入配置的告警群

## 🚧 免责声明

1. **测试阶段**：本插件目前处于测试阶段，可能存在未知的 Bug 或不稳定因素。
2. **使用建议**：强烈建议在独立的测试环境中使用本插件，不推荐直接部署到生产环境的 Bot 实例上。
3. **风险自负**：使用本插件所造成的任何直接或间接损失（包括但不限于 Bot 实例异常、数据丢失、服务中断等），插件作者概不负责。
4. **开源协议**：本插件基于 MIT 协议开源，您可以自由使用、修改和分发，但需保留原作者信息。
5. **问题反馈**：如遇到 Bug 或有功能建议，欢迎通过以下方式反馈：
   
   - 提交 [GitHub Issues](https://github.com/your-repo/nonebot-plugin-nc-status/issues)
   - 联系作者

## 📄 开源协议

本项目采用 [MIT](LICENSE) 协议开源。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

</div>

