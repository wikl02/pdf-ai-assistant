from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "pdf"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = OUT_DIR / "刘阳_AI应用开发_优化简历.pdf"
MD_PATH = OUT_DIR / "刘阳_AI应用开发_优化简历.md"

FONT = "NotoSansSC"
FONT_BOLD = "NotoSansSC-Bold"
pdfmetrics.registerFont(TTFont(FONT, r"C:\Windows\Fonts\NotoSansSC-VF.ttf"))
pdfmetrics.registerFont(TTFont(FONT_BOLD, r"C:\Windows\Fonts\simhei.ttf"))


resume = {
    "name": "刘阳",
    "meta": "男 | 24岁 | 18114703911 | 895190465@qq.com | 南京",
    "target": "求职意向：AI 应用开发工程师 / Python RAG 应用开发 | 期望薪资：5-6K",
    "summary": [
        "计算机科学与信息安全背景，当前聚焦 AI 应用开发方向，已独立完成企业知识库智能助手 MVP，覆盖文档解析、Embedding、Chroma 向量检索、DeepSeek 调用、来源标注和异常处理等完整链路。",
        "熟悉 Python、Streamlit、pypdf、python-docx、openpyxl、sentence-transformers、Chroma、OpenAI SDK/DeepSeek API，能够将业务文档问答需求拆解为可运行、可演示、可迭代的 RAG 应用。",
        "测试与运维经历带来较强的问题定位、日志分析、稳定性意识和用户支持经验，重视异常提示、数据安全、文件状态识别和知识沉淀。",
    ],
    "skills": [
        ("AI 应用与 RAG", "可完成文档加载、文本切分、Embedding、向量库入库、语义检索、上下文构造和大模型问答调用。"),
        ("Python 开发", "熟悉函数封装、异常处理、文件 IO、哈希计算、第三方库集成，能编写 Streamlit 应用和自动化脚本。"),
        ("文档解析", "支持 PDF、TXT、Markdown、DOCX、CSV、XLSX 等格式解析，了解扫描版 PDF 与 OCR 后续优化方向。"),
        ("向量检索与模型调用", "使用 sentence-transformers 生成多语言 Embedding，使用 Chroma 持久化向量数据，调用 DeepSeek API。"),
        ("工程化与安全意识", "了解 .env、API Key 保护、.gitignore、SHA-256 文件指纹、缓存优化、友好异常提示和日志分析。"),
    ],
    "projects": [
        {
            "name": "企业知识库智能助手 MVP",
            "time": "2026.07",
            "stack": "Python / Streamlit / Chroma / sentence-transformers / DeepSeek API / pypdf / python-docx / openpyxl",
            "desc": "面向企业内部资料检索和问答场景，独立开发多文档 RAG 问答应用，用户上传资料后，系统自动解析、切分、向量化并写入 Chroma，通过语义检索召回相关内容，再调用 DeepSeek 生成基于来源文本的回答。",
            "bullets": [
                "从单 PDF 问答原型升级为多文档知识库助手，支持 PDF、TXT、Markdown、DOCX、CSV、XLSX 解析，统一记录来源文档、页码、段落、行号和表格行号。",
                "设计文本切分与重叠窗口策略，使用 sentence-transformers 生成归一化 Embedding，并接入 Chroma 实现跨文档语义检索。",
                "构建检索上下文并调用 DeepSeek API，要求模型仅基于召回文本回答，降低离题和幻觉风险。",
                "补充聊天记录、知识库预览、来源文本块展开、无命中不调用 AI、API Key/余额/限流/网络失败友好提示等体验。",
                "使用 SHA-256 识别上传文件集合，通过 Streamlit 缓存减少重复解析和模型加载，并沉淀 README、进度文档和迭代路线图。",
            ],
        },
    ],
    "work": [
        {
            "company": "南京中科创达软件科技有限公司",
            "role": "测试工程师",
            "time": "2026.02-至今",
            "bullets": [
                "负责终端整机及核心应用功耗专项测试，使用 PowerTool 等工具采集待机、亮屏、高负载等场景数据。",
                "结合系统日志和软硬件行为分析异常耗电点，推动研发回归验证，具备数据分析、问题复现和质量闭环能力。",
            ],
        },
        {
            "company": "南京竞思教育",
            "role": "IT 运维与行政支持",
            "time": "2025.02-2026.02",
            "bullets": [
                "负责多校区办公终端软硬件维护、系统部署、软件安装和基础故障排查，维护物资/费用台账并完成数据统计。",
            ],
        },
        {
            "company": "联想云领（无锡）",
            "role": "运维工程师",
            "time": "2023.11-2024.06",
            "bullets": [
                "面向国内外员工提供桌面运维和远程支持，处理系统报错、软件冲突、权限配置和网络连通性问题。",
                "参与标准化装机、驱动更新、病毒查杀和资产盘点，沉淀故障根因与解决方案。",
            ],
        },
    ],
    "education": [
        "南京林业大学 | 本科 | 计算机科学与技术 | 2024-2027",
        "无锡城市职业技术学院 | 大专 | 信息安全技术 | 2021-2024",
    ],
    "certs": "软件设计师、计算机程序设计师四级、全国计算机一级、大学英语三级、IITC 工信人才专业知识测评证书等",
}


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        "CN",
        parent=styles["Normal"],
        fontName=FONT,
        fontSize=8.2,
        leading=12,
        textColor=colors.HexColor("#222222"),
        wordWrap="CJK",
        spaceAfter=2,
    )
)
styles.add(
    ParagraphStyle(
        "Small",
        parent=styles["CN"],
        fontSize=7.4,
        leading=10.2,
        textColor=colors.HexColor("#333333"),
    )
)
styles.add(
    ParagraphStyle(
        "HeaderName",
        parent=styles["CN"],
        fontName=FONT_BOLD,
        fontSize=19,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111111"),
    )
)
styles.add(
    ParagraphStyle(
        "HeaderMeta",
        parent=styles["CN"],
        fontSize=8.6,
        leading=12,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        "Section",
        parent=styles["CN"],
        fontName=FONT_BOLD,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0F4C81"),
        spaceBefore=5,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        "ItemTitle",
        parent=styles["CN"],
        fontName=FONT_BOLD,
        fontSize=8.8,
        leading=12,
    )
)
styles.add(
    ParagraphStyle(
        "Right",
        parent=styles["CN"],
        alignment=TA_RIGHT,
        fontSize=7.8,
        leading=11,
    )
)
styles.add(
    ParagraphStyle(
        "CNBullet",
        parent=styles["CN"],
        leftIndent=8,
        firstLineIndent=-8,
        fontSize=7.9,
        leading=11.2,
    )
)


def section(title):
    return Paragraph(esc(title), styles["Section"])


def bullet(text):
    return Paragraph("• " + esc(text), styles["CNBullet"])


def title_row(left, right):
    table = Table(
        [[Paragraph(esc(left), styles["ItemTitle"]), Paragraph(esc(right), styles["Right"])]],
        colWidths=[130 * mm, 40 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def build_pdf():
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=13 * mm,
    )
    story = []
    story.append(Paragraph(esc(resume["name"]), styles["HeaderName"]))
    story.append(Paragraph(esc(resume["meta"]), styles["HeaderMeta"]))
    story.append(Paragraph(esc(resume["target"]), styles["HeaderMeta"]))
    story.append(Spacer(1, 3))

    story.append(section("个人优势"))
    for item in resume["summary"]:
        story.append(bullet(item))

    story.append(section("专业技能"))
    for name, detail in resume["skills"]:
        story.append(bullet(f"{name}：{detail}"))

    story.append(section("项目经历"))
    for project in resume["projects"]:
        story.append(title_row(project["name"], project["time"]))
        story.append(Paragraph(esc(f"技术栈：{project['stack']}"), styles["Small"]))
        story.append(Paragraph(esc(project["desc"]), styles["CN"]))
        for item in project["bullets"]:
            story.append(bullet(item))
        story.append(Spacer(1, 2))

    story.append(section("工作与实习经历"))
    for job in resume["work"]:
        story.append(title_row(f"{job['company']} | {job['role']}", job["time"]))
        for item in job["bullets"]:
            story.append(bullet(item))

    story.append(section("教育经历"))
    for edu in resume["education"]:
        story.append(bullet(edu))

    story.append(section("资格证书"))
    story.append(Paragraph(esc(resume["certs"]), styles["CN"]))

    doc.build(story)


def build_markdown():
    lines = [
        f"# {resume['name']}",
        "",
        resume["meta"],
        "",
        resume["target"],
        "",
        "## 个人优势",
    ]
    lines.extend(f"- {item}" for item in resume["summary"])
    lines += ["", "## 专业技能"]
    lines.extend(f"- {name}：{detail}" for name, detail in resume["skills"])
    lines += ["", "## 项目经历"]
    for project in resume["projects"]:
        lines += [
            f"### {project['name']} | {project['time']}",
            f"技术栈：{project['stack']}",
            "",
            project["desc"],
            "",
        ]
        lines.extend(f"- {item}" for item in project["bullets"])
        lines.append("")
    lines += ["## 工作与实习经历"]
    for job in resume["work"]:
        lines.append(f"### {job['company']} | {job['role']} | {job['time']}")
        lines.extend(f"- {item}" for item in job["bullets"])
        lines.append("")
    lines += ["## 教育经历"]
    lines.extend(f"- {edu}" for edu in resume["education"])
    lines += ["", "## 资格证书", resume["certs"], ""]
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    build_pdf()
    build_markdown()
    print(PDF_PATH)
    print(MD_PATH)
