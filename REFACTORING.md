# 项目重构完成与使用指南 (Refactoring Report & User Guide)

## 1. 重构总结 (Refactoring Summary)

本项目已完成核心功能的重构与升级，实现了更高效、智能的加密货币信号监测系统。

### 已完成的改进 (Achievements)
- [x] **Catch the Trend (15min FVG)**: 成功集成基于公平价值缺口 (FVG) 的趋势捕捉策略，支持 K 线形态确认（锤头/吞没）。
- [x] **异步架构 (Async Core)**: 全面迁移至 `asyncio` 和 `aiohttp`，实现了 Binance 数据的并发获取，大幅降低延迟。
- [x] **双 AI 模型引擎**: 集成 **Google Gemini** (主) + **DeepSeek** (备) 的双模型架构，确保分析服务的连续性与高可用性。
- [x] **状态持久化**: 实现 `SignalStateManager`，支持信号去重与状态保存（基于 JSON/SQLite），防止重启后信号重复推送。
- [x] **容器化构建**: 引入基于 `micromamba` 的多阶段构建 `Dockerfile`，提供极简且一致的运行环境。

## 2. 系统架构概览

*   **入口 (Entry)**: `main.py` 运行异步事件循环，每分钟调度一次信号检查。
*   **数据层**: `data_fetcher.py` 异步并发获取多币种、多时间周期的 OHLCV 数据。
*   **策略层**: `indicators.py` 通过 `FairValueGapSignal` 等类进行即时技术分析。
*   **分析层**: `ai_interpreter.py` 优先调用 Gemini API 进行深度市场解读，失败时自动切换至 DeepSeek。
*   **通知层**: `alerter.py` 分发富文本卡片至飞书 (Lark) 和 微信 (WXPush/Cloudflare Workers)。

## 3. 安装与部署指南 (Installation & Usage)

### 3.1 环境准备

项目依赖 **Python 3.9+**，推荐使用 **Docker** 或 **Conda/Mamba** 进行环境管理。

#### 方式一：Docker 部署 (推荐)
无需本地安装 Python 环境，直接构建镜像。

1.  **构建镜像**:
    ```bash
    docker build -t crypto-bot .
    ```
2.  **配置环境文件 (.env)**:
    在项目根目录创建 `.env` 文件 (参考下文配置说明)。
3.  **运行容器**:
    ```bash
    docker run -d \
      --name crypto-bot \
      --env-file .env \
      --restart unless-stopped \
      crypto-bot
    ```

#### 方式二：本地 Conda/Mamba 开发
1.  **创建环境**:
    使用 `environment.yml` 创建一致的依赖环境。
    ```bash
    # 使用 Micromamba (推荐)
    micromamba create -f environment.yml
    micromamba activate oi-bot-env

    # 或使用 Conda
    conda env create -f environment.yml
    conda activate oi-bot-env
    ```
2.  **配置环境文件 (.env)**:
    同上。
3.  **运行**:
    ```bash
    python main.py
    ```

### 3.2 配置文件说明

#### `.env` (敏感配置)
请在项目根目录创建 `.env` 文件，填入以下必要信息：

```ini
# --- AI 模型配置 ---
# Google Gemini (主要)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/openai/  # 或自定义反代地址
GEMINI_MODEL_NAME=gemini-2.0-flash-exp # 推荐模型

# DeepSeek (备用)
DEEPSEEK_API_KEY=your_deepseek_api_key

# --- 交易所配置 ---
# Binance (可选，用于提高 API 频率限制)
BINANCE_API_KEY=your_binance_key
BINANCE_API_SECRET=your_binance_secret

# --- 通知渠道 ---
# 飞书 (Lark) Webhook
LARK_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxx-xxxx

# 微信 (WXPush via Cloudflare Workers)
WX_WEBHOOK_URL=https://your-worker.workers.dev/wxsend
WX_WEBHOOK_AUTH=your_worker_auth_token
```

#### `config.py` (策略配置)
可调整以下参数以改变机器人行为：
*   `TIMEFRAMES`: 监测的时间周期 (默认 `["15m", "1h", "4h"]`)。
*   `SYMBOLS`: 监测的币种列表。
*   `ACTIVE_SIGNALS`: 启用的信号策略类名列表 (如 `["FairValueGapSignal"]`)。
*   `FVG_REBALANCE_THRESHOLD`: FVG 回补触发阈值 (0.0-1.0)。

## 4. 目录结构说明

```text
.
├── main.py              # 程序入口 (Async Loop)
├── config.py            # 静态配置
├── environment.yml      # Conda 环境依赖
├── Dockerfile           # Docker 构建文件
├── .env                 # 环境变量 (需手动创建)
├── internal/
│   └── state/           # 状态存储 (JSON/DB)
├── data_fetcher.py      # 异步数据获取
├── indicators.py        # 信号策略实现 (FVG)
├── ai_interpreter.py    # 双模型 AI 解读逻辑
├── alerter.py           # 报警发送模块
├── state_manager.py     # 状态管理与去重
└── worker_*.js          # Cloudflare Workers 脚本 (微信推送后端)
```

## 5. 维护与除错

*   **日志**: 默认输出到控制台。Docker 模式下使用 `docker logs -f crypto-bot` 查看。
*   **状态重置**: 若需重置信号状态，可删除 `internal/state/` 目录下的 `.json` 或 `.db` 文件。
*   **新增策略**:
    1. 在 `indicators.py` 中继承基类实现新策略。
    2. 在 `config.py` 的 `ACTIVE_SIGNALS` 列表中添加类名。
