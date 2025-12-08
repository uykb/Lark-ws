# Crypto AI Trading Signal Bot

这是一个基于 Python 的自动化加密货币交易信号机器人，专门用于监控币安（Binance）的指定 USDT 永续合约。它结合了传统的市场结构分析（如 OI 激增、FVG）和 Google Gemini AI 的深度解读，通过 Discord 发送实时的高质量交易信号。

## ✨ 主要功能

- **多币种监控**: 自动获取并监控 `config.py` 中配置的主流币种（`MAJOR_COINS`）数据。
- **多维度信号检测**: 采用模块化设计，目前支持以下核心策略：
    1.  **`MomentumSpikeSignal` (动量捕捉)**: 当合约在 15 分钟内持仓量（Open Interest）激增且价格同时上涨时触发，捕捉主力资金入场迹象。支持为不同币种（如 BTC/ETH）配置独立的灵敏度阈值。
    2.  **`FairValueGapSignal` (趋势回归)**: 识别公平价值缺口（FVG），并在价格回补缺口且出现反转K线（如锤子线、射击之星）时触发，基于市场结构寻找入场点。
- **AI 智能分析**: 集成 Google `gemini-2.5-flash-lite` 模型，对每个技术信号进行二次分析。AI 会结合当前市场背景，提供专业的交易逻辑解读，辅助人工决策。
- **高效异步架构**: 使用 `asyncio` 和 `aiohttp` 并发获取数百个交易对的数据，极大降低延迟，确保信号的实时性。
- **智能状态管理**: 内置信号去重与冷却机制（`SignalStateManager`），避免同一信号在短时间内重复报警，减少噪音。
- **高度可配置**: 支持在 `config.py` 中灵活调整时间周期、各类阈值、监控列表以及 AI 模型参数。
- **Docker 化部署**: 提供基于 `micromamba` 的轻量级 Docker 镜像，支持一键构建与部署，适合 24/7 稳定运行。

## 🛠️ 安装与配置

### 1. 本地开发环境

**前置要求**:
- Python 3.9+
- Git
- Conda (推荐使用 Miniconda 或 Micromamba)

**步骤**:

1.  **克隆项目**:
    ```bash
    git clone <YOUR_REPOSITORY_URL>
    cd OI-bot
    ```

2.  **配置环境变量**:
    在项目根目录创建 `.env` 文件，并填入必要的 API 密钥：
    ```env
    # .env
    # Google Gemini API Key (支持多个Key，用逗号分隔以轮询使用)
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY_1,YOUR_GEMINI_API_KEY_2"
    
    # Discord Webhook URL (用于接收报警)
    DISCORD_WEBHOOK_URL="YOUR_DISCORD_WEBHOOK_URL"
    ```

3.  **安装依赖**:
    使用 Conda 创建并激活虚拟环境：
    ```bash
    conda env create -f environment.yml
    conda activate oi-bot-env
    ```

4.  **调整配置 (可选)**:
    修改 `config.py` 以适应你的交易风格。例如：
    - `MAJOR_COINS`: 定义需要监控的币种列表。
    - `COIN_CONFIGS`: 为 BTC、ETH 等大市值币种设置更严格的触发阈值。
    - `TIMEFRAME`: 调整 K 线周期（默认 15m）。

5.  **运行机器人**:
    ```bash
    python main.py
    ```

### 2. Docker 部署

**步骤**:

1.  **构建镜像**:
    ```bash
    docker build -t crypto-signal-bot .
    ```

2.  **运行容器**:
    确保已配置好 `.env` 文件。
    ```bash
    docker run -d --restart unless-stopped --env-file .env --name oi-bot crypto-signal-bot
    ```

## 📂 项目结构

- `main.py`: 程序入口，负责初始化、异步调度和主循环。
- `config.py`: 项目配置文件，包含 API Key 读取、策略参数和阈值设置。
- `data_fetcher.py`: 负责与币安 API 交互，异步获取市场数据。
- `indicators.py`: 包含核心的技术指标计算逻辑和信号检测类。
- `ai_interpreter.py`: 封装与 Gemini API 的交互逻辑，生成 AI 分析报告。
- `alerter.py`: 处理 Discord 消息推送。
- `state_manager.py`: 管理信号状态，处理去重和冷却逻辑。
- `logger.py`: 日志配置。

## 🤝 贡献

欢迎提交 Pull Request 或 Issue 来改进策略、增加新功能或修复 Bug。

## ⚠️ 免责声明

本机器人仅供学习和辅助分析使用，不构成任何投资建议。加密货币市场风险极高，请谨慎交易。