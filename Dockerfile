# 1. 使用官方 Miniconda3 镜像作为基础
FROM continuumio/miniconda3

# 2. 在容器内设置工作目录
WORKDIR /app

# 3. 复制依赖文件，以便利用 Docker 的缓存机制
COPY requirements.txt .

# 4. 安装项目依赖
# 使用 --no-cache-dir 减小镜像体积
RUN pip install --no-cache-dir -r requirements.txt

# 5. 复制项目的所有代码到工作目录
COPY . .

# 6. 定义容器启动时执行的默认命令
CMD ["python", "main.py"]
