# ---- Builder Stage ----
# 使用 micromamba 镜像作为构建环境
FROM mambaorg/micromamba:1.5.6 as builder

# 复制环境定义文件
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml

# 安装基础工具，包括 ca-certificates
USER root
RUN apt-get update && apt-get install -y ca-certificates openssl && rm -rf /var/lib/apt/lists/*
USER $MAMBA_USER

# 在一个单独的前缀中创建环境，并安装所有依赖
RUN micromamba create -p /tmp/env -f /tmp/environment.yml && \
    micromamba clean --all --yes

# ---- Final Stage ----
# 使用一个非常小的 "distroless" 风格镜像作为最终运行环境
FROM mambaorg/micromamba:1.5.6 as final

# 防止 Python 缓冲 stdout 和 stderr
ENV PYTHONUNBUFFERED=1

# 安装 ca-certificates 到最终镜像 (因为 final 也是基于 debian/alpine)
USER root
RUN apt-get update && apt-get install -y ca-certificates openssl && rm -rf /var/lib/apt/lists/*
USER $MAMBA_USER

# 从构建阶段复制已安装好的环境
COPY --from=builder /tmp/env /opt/conda/

# 设置工作目录
WORKDIR /app

# 复制你的应用代码
COPY . .

# 设置 PATH，以便可以直接调用 python
ENV PATH="/opt/conda/bin:$PATH"

# 定义容器启动时执行的默认命令
CMD ["python", "main.py"]
