# FastAPI 后端

## 启动

```powershell
python -m alembic upgrade head
python -m uvicorn backend.main:app --reload --port 8000
```

接口文档：`http://localhost:8000/docs`

## 数据与文件

- 业务数据库：默认 `data/app.db`
- 原始上传文件：默认 `data/uploads/`
- Chroma 向量数据：`.chroma_db/`
- 数据库迁移：`alembic/versions/`

环境变量可通过 `.env` 配置：

- `DATABASE_URL`
- `UPLOAD_STORAGE_DIR`
- `JWT_SECRET_KEY`
- `APP_USERNAME`
- `APP_PASSWORD`
- `DEEPSEEK_API_KEY`

## 主要接口

- `POST /login`：Streamlit 兼容登录接口
- `POST /upload`：Streamlit 兼容上传接口
- `POST /ask`：Streamlit 兼容问答接口
- `GET/POST /api/admin/knowledge-bases`：知识库列表与创建
- `GET /api/admin/knowledge-bases/{id}`：知识库详情
- `POST /api/admin/knowledge-bases/{id}/documents`：上传并索引文档
- `GET /api/admin/knowledge-bases/{id}/documents`：文档列表
- `DELETE /api/admin/knowledge-bases/{id}/documents/{document_id}`：删除文档及其向量块
- `POST /api/admin/knowledge-bases/{id}/documents/{document_id}/reindex`：重新索引
- `GET/POST /api/admin/users`：用户列表与创建
- `PATCH /api/admin/users/{id}/status`：禁用或启用用户
- `PATCH /api/admin/users/{id}/role`：修改角色
- `POST /api/admin/users/{id}/reset-password`：重置密码

所有 `/api/admin/*` 接口仅允许管理员访问。

## 测试

```powershell
python -m pytest -q
python -m alembic check
```
