# 阿里云 ECS 部署说明

本说明适用于 Ubuntu 22.04、2 核 4 GB 内存的阿里云 ECS。部署后由 Nginx 提供 Vue 页面并转发 FastAPI，请勿直接向公网开放 8000 或 5173 端口。

## 1. 安全组

- TCP 80：允许公网访问 HTTP。
- TCP 443：配置 HTTPS 后允许公网访问。
- TCP 22：只允许自己的公网 IP 访问。
- 不开放 8000、5173、SQLite 或 Chroma 端口。

## 2. 登录服务器

```bash
ssh root@YOUR_SERVER_IP
```

建议后续创建普通运维用户，并改用 SSH 密钥登录。

## 3. 增加 2 GB Swap

先检查是否已有 Swap：

```bash
swapon --show
```

没有输出时执行：

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

## 4. 安装 Docker

阿里云中国大陆 ECS 建议使用阿里云 Docker CE 镜像源，避免访问 Docker 海外软件源时握手失败：

```bash
apt update
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker run --rm hello-world
```

安装完成后检查：

```bash
docker --version
docker compose version
systemctl is-active docker
```
## 5. 拉取项目

```bash
sudo mkdir -p /opt/pdf-ai-assistant
sudo chown -R "$USER":"$USER" /opt/pdf-ai-assistant
git clone https://github.com/wikl02/pdf-ai-assistant.git /opt/pdf-ai-assistant
cd /opt/pdf-ai-assistant
```

## 6. 配置生产环境变量

```bash
cp .env.production.example .env.production
nano .env.production
```

生成 JWT 密钥：

```bash
openssl rand -hex 32
```

至少修改：

- `DEEPSEEK_API_KEY`
- `APP_USERNAME`
- `APP_PASSWORD`
- `JWT_SECRET_KEY`
- `CORS_ORIGINS`

`.env.production` 已加入 `.gitignore`，不要提交到 GitHub。

## 7. 构建并启动

```bash
docker compose up -d --build
```

首次构建会下载 Python、Node.js、Embedding 模型和依赖，耗时会明显长于后续启动。

查看状态和日志：

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f web
```

本机健康检查：

```bash
curl http://127.0.0.1/healthz
curl http://127.0.0.1/health
```

浏览器访问：

```text
http://YOUR_SERVER_IP
```

接口文档：

```text
http://YOUR_SERVER_IP/docs
```

## 8. 数据位置

Compose 创建以下持久卷：

- `pdf-ai-assistant_app_data`：SQLite 和上传文档。
- `pdf-ai-assistant_chroma_data`：Chroma 向量数据。
- `pdf-ai-assistant_model_cache`：Embedding 模型缓存。

执行 `docker compose down` 不会删除数据。不要执行 `docker compose down -v`，后者会删除持久卷。

## 9. 更新版本

```bash
cd /opt/pdf-ai-assistant
git pull origin main
docker compose up -d --build
docker image prune -f
```

## 10. 备份

```bash
cd /opt/pdf-ai-assistant
mkdir -p backups
docker run --rm \
  -v pdf-ai-assistant_app_data:/source:ro \
  -v "$PWD/backups":/backup \
  alpine sh -c 'tar -czf /backup/app-data-$(date +%F-%H%M).tar.gz -C /source .'

docker run --rm \
  -v pdf-ai-assistant_chroma_data:/source:ro \
  -v "$PWD/backups":/backup \
  alpine sh -c 'tar -czf /backup/chroma-data-$(date +%F-%H%M).tar.gz -C /source .'
```

备份文件仍在服务器上，重要数据应再复制到本地或对象存储。

## 11. HTTPS

当前配置先使用 HTTP 验证部署。绑定域名后，再申请 SSL 证书并为 Nginx 增加 443 配置。完成 HTTPS 后，将 `.env.production` 中的 `CORS_ORIGINS` 改为最终 HTTPS 域名并重新启动服务。

## 常用命令

```bash
docker compose ps
docker compose logs --tail=100 api
docker compose restart api
docker compose stop
docker compose start
docker stats
df -h
free -h
```
