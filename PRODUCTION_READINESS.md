# 生产就绪检查清单

本清单适用于当前的 Vue + Nginx + FastAPI + SQLite + Chroma 部署。`app.py`
继续作为 Streamlit 兼容入口保留。当前生产环境尚未使用 PostgreSQL；本文同时给出
迁移到 PostgreSQL 后的备份方式。

## 1. 认证与权限

- [x] `/api/auth/login` 和兼容 `/login` 允许匿名访问。
- [x] `/api/auth/me` 必须携带有效 JWT。
- [x] `/api/admin/*` 仅允许 `admin` 角色。
- [x] 文档上传、删除、重新索引仅允许 `admin`。
- [x] 问答和知识库目录要求已启用的 `admin` 或 `user` 账号。
- [x] 账号被禁用后，已有 JWT 也无法继续访问。
- [x] 生产环境缺失 `JWT_SECRET_KEY` 时拒绝启动。
- [x] 生产环境可通过 `API_DOCS_ENABLED=false` 关闭 Swagger/OpenAPI。
- [ ] 当前普通用户可以看到全部知识库；部门级或知识库级 ACL 尚未实现。
- [ ] 登录失败次数目前只在 Nginx 单机按 IP 限流，尚未实现账号锁定或 Redis 限流。

生产环境变量至少应包含：

```env
APP_ENV=production
API_DOCS_ENABLED=false
JWT_SECRET_KEY=<openssl rand -hex 32 的输出>
ACCESS_TOKEN_EXPIRE_MINUTES=480
CORS_ORIGINS=https://kb.example.com
ALLOWED_HOSTS=kb.example.com
```

不要在日志、截图、GitHub 或工单中暴露 JWT、密码和 API Key。

## 2. 健康检查

| 地址 | 用途 | 检查内容 |
| --- | --- | --- |
| `/health/live` | 容器存活探针 | FastAPI 进程可响应 |
| `/health/ready` | 流量就绪探针 | 数据库与 Chroma 均可访问 |
| `/health` | 兼容就绪检查 | 与 `/health/ready` 相同 |
| `/healthz` | Nginx 存活探针 | Web 容器可响应 |

验证命令：

```bash
curl -fsS http://127.0.0.1/healthz
curl -fsS http://127.0.0.1/health/live
curl -fsS http://127.0.0.1/health/ready
docker compose -f docker-compose.acr.yml ps
```

`/health/ready` 返回 HTTP 503 时不要继续发布，应先检查返回 JSON 中的
`database` 或 `chroma` 状态。

## 3. 审计日志

以下操作会写入 `pdf_ai_assistant.audit` 日志：

- 登录成功和失败；
- 创建用户、启停账号、修改角色、重置密码；
- 创建知识库；
- 上传、删除和重新索引文档；
- 用户问答。

日志记录操作者、资源 ID、文件数量、字节数、文本块数量和问题长度，不记录密码、
JWT、完整问题、文档正文或 DeepSeek API Key。

```bash
docker compose -f docker-compose.acr.yml logs --since=1h api
docker compose -f docker-compose.acr.yml logs -f api | grep pdf_ai_assistant.audit
```

Compose 已限制单个日志文件为 10 MB，保留 3 个文件。正式运行时建议把 Docker 日志
采集到阿里云日志服务 SLS，并为连续登录失败、健康检查失败和容器重启设置告警。

## 4. Docker 与 Nginx

- [x] API 仅在 Compose 网络暴露 8000，不映射到公网。
- [x] Chroma 和数据库没有公网端口。
- [x] 容器使用 `no-new-privileges`、PID 限制、健康检查和优雅停止。
- [x] 数据库、上传文件、Chroma 和模型缓存使用持久卷。
- [x] Nginx 上传限制为 50 MB，代理读取超时为 300 秒。
- [x] 登录接口按来源 IP 限流。
- [x] 已设置 CSP、点击劫持、MIME、Referrer 和 Permissions Policy 安全头。
- [x] SPA 静态资源缓存与入口页禁用缓存已分开配置。
- [ ] HTTPS、HSTS 和证书自动续期需要在服务器上配置。
- [ ] 当前镜像使用 `latest`；稳定发布应改用不可变版本或镜像 digest。

发布前执行：

```bash
docker compose -f docker-compose.acr.yml config >/dev/null
docker compose -f docker-compose.acr.yml pull
docker compose -f docker-compose.acr.yml up -d
docker compose -f docker-compose.acr.yml ps
docker compose -f docker-compose.acr.yml exec web nginx -t
```

Embedding 模型缓存位于独立持久卷。新服务器第一次索引前应先完成模型预热；不要在 ACR
个人版构建过程中下载大模型，以免超过构建时限。

## 5. 当前 SQLite 备份

当前数据卷：

- `pdf-ai-assistant_app_data`：`app.db` 和 `uploads/`；
- `pdf-ai-assistant_chroma_data`：Chroma 数据；
- `pdf-ai-assistant_model_cache`：可重新下载，不属于关键业务备份。

建议每天备份，至少保留 7 个日备份和 4 个周备份，并复制到启用服务端加密和版本控制
的阿里云 OSS。数据库、上传目录和 Chroma 必须使用同一个时间戳。

维护窗口流程：

1. 暂停 Web 流量或停止 Web 容器。
2. 使用 Python `sqlite3.Connection.backup` 生成一致的 SQLite 快照。
3. 停止 API，防止上传目录和 Chroma 在复制时变化。
4. 复制 SQLite 快照、`/app/data/uploads` 和 `/app/.chroma_db`。
5. 生成 SHA256 清单并上传 OSS。
6. 启动服务并执行就绪检查。

示例：

```bash
cd /opt/pdf-ai-assistant
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "backups/$STAMP"
docker compose -f docker-compose.acr.yml stop web
docker compose -f docker-compose.acr.yml exec -T api python -c "import sqlite3; src=sqlite3.connect('/app/data/app.db'); dst=sqlite3.connect('/app/data/app-backup.db'); src.backup(dst); dst.close(); src.close()"
API_CONTAINER=$(docker compose -f docker-compose.acr.yml ps -q api)
docker compose -f docker-compose.acr.yml stop api
docker cp "$API_CONTAINER:/app/data/app-backup.db" "backups/$STAMP/app.db"
docker cp "$API_CONTAINER:/app/data/uploads" "backups/$STAMP/uploads"
docker cp "$API_CONTAINER:/app/.chroma_db" "backups/$STAMP/chroma"
find "backups/$STAMP" -type f -print0 | sort -z | xargs -0 sha256sum > "backups/$STAMP/SHA256SUMS"
docker compose -f docker-compose.acr.yml start api web
curl -fsS http://127.0.0.1/health/ready
```

恢复前必须先备份当前数据。停止服务后恢复 `app.db`、`uploads/` 和 Chroma 到原路径，
确认文件所有者为容器内 UID `10001`，再启动服务。若 Chroma 备份损坏，可以保留数据库
和上传文件，启动后对文档执行重新索引。

至少每月在独立测试目录或测试服务器做一次恢复演练；只有完成恢复验证的备份才算有效。

## 6. PostgreSQL 备份与恢复设计

迁移到 PostgreSQL 后，应用数据使用 `pg_dump`，上传文件与 Chroma 仍按上一节备份。
三类备份必须共享同一时间戳和清单。

```bash
# 逻辑备份
docker compose exec -T db sh -c \
  'pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format=custom --no-owner --no-acl' \
  > "backups/$STAMP/postgres.dump"

# 恢复到空数据库
docker compose exec -T db sh -c \
  'pg_restore --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --clean --if-exists --no-owner --no-acl' \
  < "backups/$STAMP/postgres.dump"
```

正式 PostgreSQL 建议使用阿里云 RDS，并同时启用自动备份、跨可用区高可用、删除保护、
备份保留策略和恢复演练。不要只依赖云盘快照。

## 7. 阿里云手动配置

- [ ] 绑定域名并完成 ICP 相关要求（如适用）。
- [ ] 配置 TLS 证书、443 端口和 HTTP 到 HTTPS 跳转。
- [ ] HTTPS 启用后增加 HSTS，并把 CORS/Host 改为最终域名。
- [ ] 安全组仅开放 80/443；22 仅允许管理员固定 IP。
- [ ] 禁止密码 SSH 登录，使用普通运维用户、密钥和 `sudo`。
- [ ] 配置 SLS 日志采集和健康检查告警。
- [ ] 配置 OSS 异地备份、生命周期、加密和版本控制。
- [ ] 配置磁盘、内存、Swap、容器重启次数和 DeepSeek 额度告警。
- [ ] 将 ACR `latest` 发布改为版本号或 digest，并保留回滚版本。

## 8. 上线验收

- [ ] 管理员和普通用户登录成功，错误密码被拒绝。
- [ ] 普通用户访问所有 `/api/admin/*` 均返回 403。
- [ ] 上传各支持格式，状态变为 `ready` 且文本块数量大于 0。
- [ ] 删除单个文档不会删除同知识库其他文档向量。
- [ ] 问答返回答案和来源，余额不足时显示友好提示。
- [ ] 重启容器后用户、知识库、文件和问答仍正常。
- [ ] 备份生成、SHA256 校验和恢复演练成功。
- [ ] 外网扫描确认 8000、数据库和 Chroma 端口未开放。
- [ ] 浏览器无混合内容、CORS 或 CSP 错误。
