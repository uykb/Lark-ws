# 项目功能重构说明文档

## 1. 引言
本说明文档旨在概述 OI-bot 加密货币交易信号机器人的重构计划，以增强其功能、提高代码的可维护性和扩展性。主要目标是实现 `README.md` 中提及的“Catch the Trend (15min FVG)”信号，并对现有架构进行优化，为未来的功能扩展打下基础。

## 2. 核心重构目标
*   **实现“Catch the Trend (15min FVG)”信号**：集成基于公平价值缺口 (Fair Value Gap, FVG) 的趋势捕捉信号，作为新的交易策略。
*   **改进信号检测器的灵活性**：使 `indicators.py` 能够更容易地集成和管理多种信号检测逻辑。
*   **增强配置管理**：为新信号添加必要的配置项，并考虑未来更灵活的配置方式。
*   **持久化信号状态**：解决机器人重启后信号状态丢失的问题。
*   **优化数据获取**：探索异步数据获取以提高效率。
*   **提升代码健壮性**：改善错误处理和日志记录。

## 3. 模块化改进

### 3.1 `indicators.py` - 信号检测器重构
*   **抽象基类/接口**：引入一个 `BaseSignal` 抽象基类或接口，定义 `check(self, df: pd.DataFrame)` 方法和 `signal_name` 属性，确保所有信号检测器遵循统一的结构。
*   **新信号实现**：
    *   **`FairValueGapSignal` 类**：实现“Catch the Trend (15min FVG)”逻辑。该信号将检测 FVG，等待价格回补，并在确认趋势反转K线时触发。
        *   **检测 FVG**：识别价格图表中的 FVG 模式。
        *   **回补确认**：检查价格是否回补了 FVG。
        *   **反转K线**：识别特定形态（如锤头、吞没）的反转K线作为最终触发条件。
*   **信号管理器**：在 `indicators.py` 中或引入一个新的文件 `signal_manager.py`，负责加载和管理所有信号检测器，允许 `main.py` 迭代调用。

### 3.2 `config.py` - 配置增强
*   **新增 FVG 信号配置**：
    *   `FVG_REBALANCE_THRESHOLD`：价格回补 FVG 的阈值。
    *   `FVG_CONFIRMATION_CANDLE_TYPE`：定义确认反转K线的类型。
    *   其他 FVG 相关的参数。
*   **信号列表配置**：可以考虑在 `config.py` 中定义一个列表，列出需要激活的信号检测器类名称，使信号的启用/禁用更灵活。

### 3.3 `data_fetcher.py` - 异步优化
*   **引入 `asyncio` 和 `aiohttp`**：重写 `get_all_usdt_futures_symbols` 和 `get_binance_data`，使用异步 HTTP 请求并行获取多个交易对的数据，显著提高数据获取效率。
*   **批量数据获取**：探索币安 API 是否支持一次性获取多个 symbol 的数据，进一步减少请求次数。

### 3.4 `state_manager.py` - 持久化
*   **文件存储**：将 `self.last_triggered_signals` 存储到本地 JSON 文件或 SQLite 数据库中。
    *   **加载**：在 `__init__` 中尝试从文件加载历史状态。
    *   **保存**：在 `_update_state` 或定时任务中将当前状态保存到文件。
*   **定期清理**：实现一个机制定期清理过期的信号状态，避免文件过大。

### 3.5 `main.py` - 适配与协调
*   **信号注册**：在 `main.py` 中初始化所有激活的信号检测器（根据 `config.py` 或新的信号管理器）。
*   **迭代检查**：修改 `run_check` 函数，使其能够迭代调用所有注册的信号检测器。
*   **异步集成**：如果 `data_fetcher.py` 变为异步，`main.py` 中的调度和数据流也需要调整为异步模式。

## 4. 实施步骤（初步）
1.  **创建 `REFACTORING.md` 文件** (在 `ACT MODE` 下执行)。
2.  **重构 `indicators.py`**：
    *   定义 `BaseSignal` 抽象类。
    *   将 `MomentumSpikeSignal` 适配到 `BaseSignal`。
    *   实现 `FairValueGapSignal` 类。
3.  **更新 `config.py`**：添加 FVG 信号相关的配置参数。
4.  **修改 `main.py`**：适配新的信号检测器结构，使其能够同时运行多个信号。
5.  **重构 `state_manager.py`**：实现信号状态的持久化到文件。
6.  **优化 `data_fetcher.py`**：实现异步数据获取。
7.  **完善错误处理和日志记录**：在关键模块中增加更详细的错误捕获和日志输出。
8.  **测试**：对新旧功能进行单元测试和集成测试。
