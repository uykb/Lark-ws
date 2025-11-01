# Crypto Indicator Alerts

这是一个自动化的加密货币市场指标监控机器人。它能监控币安期货市场的热门币种，检测成交量、持仓量、多空比等关键指标的异动，并利用 AI 对信号进行综合分析，最终通过 Discord 发送实时警报。

## ✨ 主要功能

- **动态币种监控**: 自动跟踪并监控币安期货市场上流动性最高的 N 个币种，无需手动配置。
- **多维度指标分析**: 监控成交量 (Volume)、持仓量 (Open Interest)、多空比 (Long/Short Ratio) 和 CVD (Cumulative Volume Delta) 的异动。
- **AI 驱动的深度解读**: 不仅仅是简单的信号提醒！AI 会结合触发信号以及包含近期K线、RSI、EMA 等指标在内的“市场快照”，提供专业的综合分析。
- **Docker 化与 CI/CD**: 内置 `Dockerfile` 和 GitHub Actions 工作流，实现从代码推送到 `ghcr.io` 镜像发布的自动化流程，完美适配云原生部署。
- **高度可配置**: 几乎所有参数（如监控阈值、动态/静态模式、监控币种数量）都可以在 `config.py` 中轻松调整。

---

## 🚀 快速开始

### 1. 本地开发与运行

**前提**:
- Python 3.8+
- Git

**步骤**:
1. **克隆仓库**:
   ```bash
   git clone <YOUR_REPOSITORY_URL>
   cd crypto_indicator_alerts
   ```

2. **创建并配置 `.env` 文件**:
   复制 `.env.example` (如果存在) 或手动创建一个 `.env` 文件，并填入您的密钥：
   ```env
   # .env
   GEMINI_API_KEY="YOUR_CUSTOM_API_KEY"
   DISCORD_WEBHOOK_URL="YOUR_DISCORD_WEBHOOK_URL"
   ```

3. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

4. **运行程序**:
   ```bash
   python main.py
   ```

---

### 2. 通过 Docker 运行

**前提**:
- Docker 已安装并运行

**步骤**:
1. **构建镜像**:
   在项目根目录 (`crypto_indicator_alerts`) 下运行：
   ```bash
   docker build -t crypto-alerts .
   ```

2. **运行容器**:
   确保 `.env` 文件已配置好，然后运行：
   ```bash
   docker run --rm --env-file .env crypto-alerts
   ```

---

## ☁️ 云平台部署 (以 claw.cloud 为例)

本项目已为您配置好完整的 CI/CD 流程，部署到云平台非常简单。

### 部署流程概览

1.  **推送代码**: 您将本地代码推送到 GitHub 仓库的 `main` 分支。
2.  **自动构建**: GitHub Actions 会被自动触发，构建 Docker 镜像。
3.  **自动发布**: 构建成功后，镜像会被推送到 GitHub Container Registry (`ghcr.io`)。
4.  **云端拉取与部署**: 您的云平台 (如 `claw.cloud`) 会检测到新镜像，自动拉取并部署新版本。

### 首次部署步骤

1. **创建 GitHub 仓库并推送代码**:
   - 在 GitHub 上创建一个新的仓库。
   - 将本项目的所有文件（包括 `.github` 文件夹）推送到该仓库的 `main` 分支。

2. **检查镜像发布**:
   - 推送后，进入您 GitHub 仓库的 "Actions" 标签页，您会看到一个正在运行的工作流。
   - 待其成功完成后，您的 Docker 镜像就已经发布到了 `ghcr.io`。镜像地址通常为 `ghcr.io/<YOUR_GITHUB_USERNAME>/<YOUR_REPOSITORY_NAME>:latest`。

3. **在 claw.cloud (或类似平台) 上配置部署**:
   - **创建新服务**: 在您的云平台上，选择从一个已有的 Docker 镜像部署。
   - **镜像地址**: 填入您在 `ghcr.io` 上的镜像地址。
   - **配置环境变量**: 这是**最关键**的一步。在平台的服务设置中，找到 "Environment Variables" 或 "Secrets" 部分，添加以下两个变量：
     - `GEMINI_API_KEY`: 填入您的 AI API 密钥。
     - `DISCORD_WEBHOOK_URL`: 填入您的 Discord Webhook URL。
   - **自动部署 (可选)**: 大多数平台都支持配置 Webhook。您可以将平台提供的 Webhook URL 添加到您 GitHub 仓库的 `Settings -> Webhooks` 中，这样每当有新镜像推送到 `ghcr.io` 时，云平台就会自动拉取并更新服务。

4. **启动服务**:
   - 保存配置并启动服务。您的监控机器人现在已经在云端 24/7 运行了！
