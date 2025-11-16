# Crypto Trading Signal Bot

This is an automated crypto trading signal bot that monitors all USDT perpetual futures on Binance. It identifies high-probability trading opportunities based on specific market structure patterns and sends real-time, AI-enhanced alerts via Discord.

## ✨ Main Features

- **Comprehensive Market Monitoring**: Automatically fetches and monitors **all** USDT perpetual futures contracts on Binance, ensuring no opportunity is missed.
- **Advanced Signal Detection**: Implements two specific, high-impact alert rules:
    1.  **Catch the Rise (15min)**: Triggers an alert when a contract's Open Interest increases by over 5% and its price simultaneously rises by over 2% within a single 15-minute candle, capturing moments of explosive momentum.
    2.  **Catch the Trend (15min FVG)**: Identifies Fair Value Gaps (FVGs), waits for the price to rebalance within the gap, and then triggers an alert on a confirmed trend reversal candle, allowing for strategic entries based on market structure.
- **AI-Powered In-depth Analysis**: Each alert is enriched with an AI-generated analysis that interprets the signal in the context of the broader market, providing a professional, data-driven thesis for the potential trade.
- **Dockerized & CI/CD Ready**: Comes with a `Dockerfile` and GitHub Actions workflow for automated building and deployment to cloud platforms, making it easy to run 24/7.
- **Simplified Configuration**: Key parameters are easily adjustable in the `config.py` file.

---

## 🚀 Quick Start

### 1. Local Development

**Prerequisites**:
- Python 3.8+
- Git

**Steps**:
1.  **Clone the repository**:
    ```bash
    git clone <YOUR_REPOSITORY_URL>
    cd <YOUR_PROJECT_DIRECTORY>
    ```

2.  **Create and configure the `.env` file**:
    Create a file named `.env` in the project root and add your API keys:
    ```env
    # .env
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    DISCORD_WEBHOOK_URL="YOUR_DISCORD_WEBHOOK_URL"
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the bot**:
    ```bash
    python main.py
    ```

---

### 2. Running with Docker

**Prerequisites**:
- Docker installed and running

**Steps**:
1.  **Build the Docker image**:
    ```bash
    docker build -t crypto-signal-bot .
    ```

2.  **Run the container**:
    Make sure your `.env` file is configured, then run:
    ```bash
    docker run --rm --env-file .env crypto-signal-bot
    ```

---

## ☁️ Cloud Deployment

This project is configured for easy CI/CD deployment to cloud platforms that support Docker.

### Deployment Overview

1.  **Push to GitHub**: Pushing code to the `main` branch triggers the GitHub Actions workflow.
2.  **Automated Build**: The workflow automatically builds the Docker image.
3.  **Publish to GHCR**: The new image is pushed to the GitHub Container Registry (`ghcr.io`).
4.  **Deploy on Cloud**: Your cloud platform detects the new image and automatically deploys the latest version of the bot.

### First-Time Deployment Steps

1.  **Create a GitHub repository** and push the project files.
2.  **Verify Image Publication**: After the first push, check the "Actions" tab in your repository to confirm the workflow ran successfully and the image is available at `ghcr.io/<YOUR_GITHUB_USERNAME>/<YOUR_REPOSITORY_NAME>:latest`.
3.  **Configure Cloud Service**:
    -   Create a new service on your cloud platform, deploying from an existing Docker image.
    -   Use the image URL from `ghcr.io`.
    -   **Crucially**, set the `GEMINI_API_KEY` and `DISCORD_WEBHOOK_URL` as environment variables or secrets in your cloud service's settings.
4.  **Launch the service** to have your bot running 24/7 in the cloud.
