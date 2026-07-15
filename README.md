# 智能 PDF 知识库问答助手

这是一个基于 Streamlit 的轻量级 PDF 知识库问答项目。用户可以上传 PDF 文件，系统会提取 PDF 文本，将内容切分为多个文本块，并根据用户问题进行关键词检索，再调用 DeepSeek API 生成基于文档内容的回答。

项目适合作为 AI 应用开发入门作品，也可以作为简历中的 RAG 问答项目原型。

## 功能特点

- 上传 PDF 文件并提取文本内容
- 自动判断扫描版或无法提取文字的 PDF
- 将 PDF 文本按块切分，降低一次性输入过长的问题
- 根据用户问题进行关键词检索，筛选相关文本块
- 调用 DeepSeek API 进行文档问答
- 回答时提示信息来源，包含页码和行号范围
- 支持聊天记录展示
- 支持清空聊天记录
- 对常见 API 异常进行友好提示，例如余额不足、Key 无效、请求限流、网络连接失败等

## 技术栈

- Python
- Streamlit
- pypdf
- DeepSeek API
- OpenAI Python SDK
- python-dotenv

## 项目结构

```text
pdf-ai-assistant/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore
```

说明：

- `app.py`：项目主程序
- `requirements.txt`：项目依赖列表
- `README.md`：项目说明文档
- `.env.example`：环境变量示例文件，不存放真实 API Key
- `.gitignore`：Git 忽略规则，避免上传 `.env`、虚拟环境等本地文件

## 环境准备

建议使用 Python 3.10 或更高版本。

创建并激活虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
pip install -r requirements.txt
```

## 配置 API Key

在项目根目录创建 `.env` 文件，并填写 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
```

注意：`.env` 文件包含敏感信息，不要上传到 GitHub。

可以创建 `.env.example` 作为示例：

```env
DEEPSEEK_API_KEY=your_api_key_here
```

## 运行项目

在项目根目录执行：

```powershell
python -m streamlit run app.py
```

运行成功后，浏览器会打开：

```text
http://localhost:8501
```

## 使用流程

1. 上传一个 PDF 文件
2. 等待系统读取并提取 PDF 文本
3. 在输入框中输入问题
4. 点击“提交问题”
5. 查看 AI 回答和检索到的相关文本来源

## 当前版本说明

当前版本采用关键词检索方式筛选相关 PDF 文本块，适合作为 RAG 问答项目的入门版本。

页码和行号基于 PDF 提取后的文本计算，可能与复杂排版 PDF 中的视觉行号略有差异。

## 后续优化方向

- 接入向量数据库，例如 Chroma 或 FAISS
- 使用 Embedding 进行语义检索
- 支持多 PDF 文档管理
- 增加 OCR 能力，支持扫描版 PDF
- 增加用户登录和历史记录持久化
- 优化前端界面和交互体验
- 增加单元测试和部署说明

## 简历描述参考

智能 PDF 知识库问答助手：基于 Python、Streamlit、pypdf 和 DeepSeek API 开发的 PDF 问答应用，实现 PDF 文本提取、文本分块、关键词检索、来源标注、聊天记录和 API 异常处理，完成了轻量级 RAG 问答原型。

