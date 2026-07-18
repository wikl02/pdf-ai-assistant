# 第二阶段：企业知识库管理后端

日期：2026-07-18

状态：已完成

本阶段完成：

- 引入 Alembic 数据库迁移，当前版本 `20260718_0002`
- 新增 `knowledge_bases`、`documents`、`knowledge_base_documents` 表
- 原始文件保存到 `data/uploads/`，数据库记录文件元数据和处理状态
- 数据库知识库与 Chroma collection 建立固定关联
- Chroma 文本块增加 `document_id`，支持单文档精准删除和重新索引
- 增加知识库列表、创建、详情接口
- 增加文档上传、列表、删除、重新索引接口
- 增加用户列表、创建、禁用/启用、角色修改、密码重置接口
- 管理员接口增加角色权限校验，普通用户访问返回 403
- 保留 Streamlit `app.py` 以及 `/login`、`/upload`、`/ask` 兼容接口
- 新增迁移、权限、文档生命周期、Chroma 精准删除和用户管理测试

验证结果：

- `python -m alembic check`：通过
- `python -m pytest -q`：5 passed
- 本地 HTTP 登录、权限、上传、列表、删除、重新索引：通过

下一步建议：

- 第三阶段开发 Vue 管理页面，对接本阶段管理员接口
- 增加知识库删除、编辑与分页查询
- 增加审计日志、操作记录和更细粒度的知识库权限
