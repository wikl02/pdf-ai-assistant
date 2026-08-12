from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT_DIR / "sample_documents" / "员工制度手册.pdf"


def register_chinese_font() -> str:
    candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]
    for font_path in candidates:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("Chinese", str(font_path), subfontIndex=0))
            return "Chinese"
    raise FileNotFoundError("未找到可用的中文字体，请安装微软雅黑或宋体。")


def draw_page_number(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Chinese", 9)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawCentredString(A4[0] / 2, 13 * mm, f"第 {document.page} 页")
    canvas.restoreState()


def build_handbook() -> None:
    font_name = register_chinese_font()
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ChineseTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=24,
        leading=34,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111827"),
        spaceAfter=18,
        wordWrap="CJK",
    )
    heading = ParagraphStyle(
        "ChineseHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=16,
        leading=24,
        textColor=colors.HexColor("#111827"),
        spaceBefore=18,
        spaceAfter=9,
        wordWrap="CJK",
    )
    body = ParagraphStyle(
        "ChineseBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=12,
        leading=22,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=8,
        wordWrap="CJK",
    )
    note = ParagraphStyle(
        "ChineseNote",
        parent=body,
        fontSize=10.5,
        leading=19,
        textColor=colors.HexColor("#475569"),
        borderColor=colors.HexColor("#CBD5E1"),
        borderWidth=0.6,
        borderPadding=9,
        backColor=colors.HexColor("#F8FAFC"),
        spaceBefore=18,
    )

    document = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        rightMargin=28 * mm,
        leftMargin=28 * mm,
        topMargin=25 * mm,
        bottomMargin=24 * mm,
        title="员工制度手册",
        author="企业知识库智能助手测试项目",
    )

    story = [Paragraph("员工制度手册", title)]
    sections = [
        (
            "1. 年假与请假制度",
            [
                "员工累计工作已满 1 年不满 10 年的，每年享有 5 天带薪年假；已满 10 年不满 20 年的，每年享有 10 天；已满 20 年的，每年享有 15 天。",
                "新入职员工的当年度年假按照剩余日历天数折算。年假申请原则上需要至少提前 3 个工作日提交，并由直属主管审批。",
                "病假需要在当天 10:00 前告知主管，并在返岗后补充病假证明。",
            ],
        ),
        (
            "2. 报销制度",
            [
                "差旅报销需要在行程结束后 7 个自然日内提交发票和行程单。",
                "普通费用报销在审批通过后 5 个工作日内打款。",
            ],
        ),
        (
            "3. 远程办公",
            [
                "远程办公每周最多 2 天，需要提前在系统中登记并获得团队负责人确认。",
            ],
        ),
    ]
    for section_title, paragraphs in sections:
        story.append(Paragraph(section_title, heading))
        story.extend(Paragraph(text, body) for text in paragraphs)

    story.extend(
        [
            Spacer(1, 4 * mm),
            Paragraph(
                "测试问题示例：员工每年有多少天年假？年假需要提前多久申请？报销多久能到账？远程办公每周几天？",
                note,
            ),
        ]
    )
    document.build(story, onFirstPage=draw_page_number, onLaterPages=draw_page_number)


if __name__ == "__main__":
    build_handbook()
    print(OUTPUT_PATH)
