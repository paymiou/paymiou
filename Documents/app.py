import os
import io
import datetime
import urllib.request
import base64
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ----------------------------------------------------------------------
# 專案配置與票價對照表
# ----------------------------------------------------------------------
PROJECT_CONFIG = {
    "茶博專案": {
        "dept": "茶博 610055",
        "default_city": "南投草屯",
        "default_reason": "茶農拜訪",
        "cities": ["南投草屯", "南投", "南投名間", "南投竹山"],
        "fares": {
            "南投草屯": {"type": "客運", "name": "草屯", "fare": 202},
            "南投":     {"type": "客運", "name": "南投", "fare": 212},
            "南投名間": {"type": "客運", "name": "名間", "fare": 322},
            "南投竹山": {"type": "客運", "name": "竹山", "fare": 296},
        }
    },
    "高美專案": {
        "dept": "高美生態 620038",
        "default_city": "台中清水",
        "default_reason": "農友拜訪",
        "cities": ["台中清水", "台中豐原"],
        "fares": {
            "台中清水": {"type": "火車", "name": "清水", "fare": 134},
            "台中豐原": {"type": "火車", "name": "豐原", "fare": 96},
        }
    }
}

# ----------------------------------------------------------------------
# 自動下載與註冊中文字型
# ----------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def init_chinese_font():
    font_name = 'CustomChineseFont'
    font_filename = 'NotoSansTC-Regular.ttf'
    
    if os.path.exists(font_filename):
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_filename))
            return font_name
        except Exception:
            pass

    possible_paths = [
        r'C:\Windows\Fonts\msjh.ttc',
        r'C:\Windows\Fonts\kaiu.ttf',
        r'C:\Windows\Fonts\msjh.ttf'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                return font_name
            except Exception:
                continue

    url = "https://cdn.jsdelivr.net/npm/@electron-fonts/noto-sans-tc@1.2.0/fonts/NotoSansTC-Regular.ttf"
    
    try:
        import pyodide.http
        content = pyodide.http.open_url(url).read()
        with open(font_filename, "wb") as f:
            f.write(content)
        pdfmetrics.registerFont(TTFont(font_name, font_filename))
        return font_name
    except Exception:
        pass

    try:
        urllib.request.urlretrieve(url, font_filename)
        pdfmetrics.registerFont(TTFont(font_name, font_filename))
        return font_name
    except Exception:
        pass

    return 'Helvetica'

# ----------------------------------------------------------------------
# 數字轉國字大寫工具
# ----------------------------------------------------------------------
def number_to_chinese_capital(num):
    try:
        num = int(num)
    except (ValueError, TypeError):
        return ""
    
    digits = ["零", "壹", "貳", "參", "肆", "伍", "陸", "柒", "捌", "玖"]
    units = ["", "拾", "佰", "仟"]
    big_units = ["", "萬", "億"]
    
    if num == 0:
        return "零"
    
    str_num = str(num)
    length = len(str_num)
    result = ""
    
    for i, digit in enumerate(str_num):
        n = int(digit)
        pos = length - 1 - i
        u = pos % 4
        bu = pos // 4
        
        if n != 0:
            result += digits[n] + units[u]
        else:
            if not result.endswith("零") and u != 0:
                result += "零"
                
        if u == 0 and bu > 0:
            if result.endswith("零"):
                result = result[:-1]
            result += big_units[bu]
            
    return result.rstrip("零")

# ----------------------------------------------------------------------
# 生成 PDF 核心邏輯 (姓名欄位加寬至 260pt)
# ----------------------------------------------------------------------
def generate_pdf_bytes(form_data, font_name):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20,
        rightMargin=20,
        topMargin=15,
        bottomMargin=15
    )
    story = []
    styles = getSampleStyleSheet()
    
    c_style = ParagraphStyle('C', parent=styles['Normal'], fontName=font_name, fontSize=12, leading=15, alignment=1)
    c_left = ParagraphStyle('CL', parent=c_style, alignment=0)
    c_right = ParagraphStyle('CR', parent=c_style, alignment=2)

    c_style_10 = ParagraphStyle('C10', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=13, alignment=1)
    c_left_10 = ParagraphStyle('CL10', parent=c_style_10, alignment=0)
    c_target_style = ParagraphStyle('CTarget', parent=styles['Normal'], fontName=font_name, fontSize=9.5, leading=11.5, alignment=0)

    title_style = ParagraphStyle('Title', parent=c_style, fontName=font_name, fontSize=16, leading=18)
    subtitle_style = ParagraphStyle('SubTitle', parent=c_style, fontName=font_name, fontSize=13, leading=15)
    meta_left = ParagraphStyle('MetaL', parent=c_left, fontName=font_name, fontSize=9.5, leading=12)
    meta_right = ParagraphStyle('MetaR', parent=c_right, fontName=font_name, fontSize=9.5, leading=12)

    def p(text, style=c_style):
        return Paragraph(str(text) if text else "", style)

    top_meta = [
        [
            p("編號：4-AB-c023(1.0)<br/>版次：1.0", meta_left),
            p("國內外出差旅費報告單", c_style),
            p("制定單位：幕僚總部人資課<br/>修訂日期：2019/09/10", meta_right)
        ]
    ]
    t_top = Table(top_meta, colWidths=[140, 275, 140], rowHeights=28)
    t_top.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(t_top)
    story.append(Spacer(1, 4))

    story.append(p("財團法人慈心有機農業發展基金會", title_style))
    story.append(Spacer(1, 8))
    story.append(p("國內外出差旅費報告單", subtitle_style))
    story.append(Spacer(1, 4))

    col_w = [22, 22, 125, 45, 30, 30, 30, 30, 60, 40, 45, 66]
    data = []

    # Row 0: 基本資料 1
    data.append([
        p("姓 名"), "", p(form_data.get('name', ''), c_left), "", "", "", "",
        p("單位代號名稱及職稱", c_style_10), "", p(form_data.get('dept', ''), c_left), "", ""
    ])

    # Row 1: 基本資料 2
    data.append([
        p("出差事由", c_style_10), "", p(form_data.get('reason', ''), c_left_10), "", "", "",
        p("出差國家及城市", c_style_10), "", "", p(form_data.get('city', ''), c_left), "", ""
    ])

    # Row 2: 出差時間
    y1, m1, d1 = form_data.get('y1', ''), form_data.get('m1', ''), form_data.get('d1', '')
    y2, m2, d2 = form_data.get('y2', ''), form_data.get('m2', ''), form_data.get('d2', '')
    days, receipts = form_data.get('days', ''), form_data.get('receipts', '')
    
    time_str = f"民國 {y1} 年 {m1} 月 {d1} 日起至民國 {y2} 年 {m2} 月 {d2} 日止共計 {days} 天/附單據 {receipts} 張/匯率："
    data.append([p("出差時間", c_style_10), "", p(time_str, c_left_10), "", "", "", "", "", "", "", "", ""])

    # Row 3 & 4: 表頭
    data.append([
        p(f"{y1} 年"), "", p("行 程"),
        p("交 通 費"), "", "",
        p("膳 費"), p("宿 費"),
        p("其 他 費 用"), "",
        p("私車油資<br/>補貼", c_style_10), p("合 計")
    ])
    data.append([
        p("月"), p("日"), "",
        p("大眾交通工具", c_style_10), p("飛機", c_style_10), p("計程車", c_style_10),
        "", "",
        p("摘 要"), p("金額"),
        "", ""
    ])

    expenses = form_data.get('expenses', [])
    total_amount = 0
    exp_count = len(expenses)
    num_exp_rows = exp_count + 1

    for i in range(num_exp_rows):
        if i < exp_count:
            item = expenses[i]
            pub = int(item.get('public_trans', 0) or 0)
            flight = int(item.get('flight', 0) or 0)
            taxi = int(item.get('taxi', 0) or 0)
            meal = int(item.get('meal', 0) or 0)
            stay = int(item.get('stay', 0) or 0)
            amt = int(item.get('amount', 0) or 0)
            gas = int(item.get('gas_subsidy', 0) or 0)

            row_total = pub + flight + taxi + meal + stay + amt + gas
            total_amount += row_total

            data.append([
                p(item.get('m', '')), p(item.get('d', '')), p(item.get('route', ''), c_left_10),
                p(str(pub) if pub else ""), p(str(flight) if flight else ""), p(str(taxi) if taxi else ""),
                p(str(meal) if meal else ""), p(str(stay) if stay else ""),
                p(item.get('other_desc', ''), c_style), p(str(amt) if amt else "", c_style),
                p(str(gas) if gas else "", c_style_10),
                p(str(row_total) if row_total else "", c_style)
            ])
        else:
            data.append([""] * 12)

    total_row_idx = len(data)
    data.append([p("總 計", c_style), "", "", "", "", "", "", "", "", "", "", p(str(total_amount), c_style)])

    report_title_row_idx = len(data)
    data.append([p("出 差 報 告"), "", "", "", "", "", "", "", "", "", "", ""])

    rep_header1_idx = len(data)
    data.append([
        p(f"{y1} 年"), "", p("訪洽公司/機構名稱<br/>及接洽人員姓名"), "", "", "",
        p("洽 辦 事 項 說 明"), "", "", "", "", ""
    ])
    rep_header2_idx = len(data)
    data.append([p("月"), p("日"), "", "", "", "", "", "", "", "", "", ""])

    reports = form_data.get('reports', [])
    rep_count = len(reports)
    num_rep_rows = rep_count + 1

    rep_start_idx = len(data)
    for i in range(num_rep_rows):
        if i < rep_count:
            rep = reports[i]
            target_str = rep.get('target', '').replace('\n', '<br/>')
            detail_str = rep.get('detail', '').replace('\n', '<br/>')
            data.append([
                p(rep.get('m', '')), p(rep.get('d', '')),
                p(target_str, c_target_style), "", "", "",
                p(detail_str, c_left), "", "", "", "", ""
            ])
        else:
            data.append([""] * 12)
    rep_end_idx = len(data) - 1

    row_heights = [25, 25, 25, 25, 25]
    for _ in range(num_exp_rows):
        row_heights.append(35)
    row_heights.append(25)
    row_heights.append(25)
    row_heights.append(25)
    row_heights.append(25)
    for _ in range(num_rep_rows):
        row_heights.append(48)

    t_style = [
        ('GRID', (0, 0), (-1, total_row_idx), 0.5, colors.black),
        ('LINEABOVE', (0, report_title_row_idx), (11, report_title_row_idx), 0.5, colors.black),
        ('LINEBELOW', (0, report_title_row_idx), (11, report_title_row_idx), 0.5, colors.black),
        ('GRID', (0, rep_header1_idx), (-1, rep_end_idx), 0.5, colors.black),

        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),

        # Row 0：姓名欄位加寬，涵蓋 cols 2~6 (寬度大幅增加至 260pt)
        ('SPAN', (0, 0), (1, 0)), ('SPAN', (2, 0), (6, 0)),
        ('SPAN', (7, 0), (8, 0)), ('SPAN', (9, 0), (11, 0)),

        # Row 1：出差事由與城市
        ('SPAN', (0, 1), (1, 1)), ('SPAN', (2, 1), (5, 1)),
        ('SPAN', (6, 1), (8, 1)), ('SPAN', (9, 1), (11, 1)),

        ('SPAN', (0, 2), (1, 2)), ('SPAN', (2, 2), (11, 2)),

        ('SPAN', (0, 3), (1, 3)),
        ('SPAN', (2, 3), (2, 4)),
        ('SPAN', (3, 3), (5, 3)),
        ('SPAN', (6, 3), (6, 4)),
        ('SPAN', (7, 3), (7, 4)),
        ('SPAN', (8, 3), (9, 3)),
        ('SPAN', (10, 3), (10, 4)),
        ('SPAN', (11, 3), (11, 4)),

        ('SPAN', (0, total_row_idx), (10, total_row_idx)),
        ('SPAN', (0, report_title_row_idx), (11, report_title_row_idx)),

        ('SPAN', (0, rep_header1_idx), (1, rep_header1_idx)),
        ('SPAN', (2, rep_header1_idx), (5, rep_header2_idx)),
        ('SPAN', (6, rep_header1_idx), (11, rep_header2_idx)),
    ]

    for r in range(rep_start_idx, rep_end_idx + 1):
        t_style.append(('SPAN', (2, r), (5, r)))
        t_style.append(('SPAN', (6, r), (11, r)))

    table = Table(data, colWidths=col_w, rowHeights=row_heights)
    table.setStyle(TableStyle(t_style))
    story.append(table)

    story.append(Spacer(1, 12))

    capital_amt = number_to_chinese_capital(total_amount)
    capital_text = f"茲領到上列旅費計新台幣 <font size=\"16\"><b>{capital_amt}</b></font> 元整"

    pay_method = form_data.get('payment_method', '個人')
    if pay_method == "匯款":
        pay_text = "款付 □個人  ■匯款 / □領現金金額："
    elif pay_method == "領現金":
        pay_text = "款付 □個人  □匯款 / ■領現金金額："
    else:
        pay_text = "款付 ■個人  □匯款 / □領現金金額："

    approval_data = [
        [
            p("核定：", c_left), "", "", "",
            p("覆核：", c_left), "", "", "",
            p("出差人：", c_left), "", "", ""
        ],
        [
            p("款付旅行社金額：", c_left), "", "", "", "",
            p(pay_text, c_left), "", "", "", "", "", ""
        ],
        [
            p(capital_text, c_left), "", "", "", "", "", "", "",
            p("領款人簽章：", c_left), "", "", ""
        ]
    ]

    t_approval_style = [
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),

        ('SPAN', (0, 0), (3, 0)), ('SPAN', (4, 0), (7, 0)), ('SPAN', (8, 0), (11, 0)),
        ('SPAN', (0, 1), (4, 1)), ('SPAN', (5, 1), (11, 1)),
        ('SPAN', (0, 2), (7, 2)), ('SPAN', (8, 2), (11, 2)),
    ]

    t_approval = Table(approval_data, colWidths=col_w, rowHeights=30)
    t_approval.setStyle(TableStyle(t_approval_style))
    story.append(t_approval)

    story.append(Spacer(1, 10))

    notes = (
        "備註：<br/>"
        "1. 依稅法規定，出差報告請逐日填寫，並附相關業務報告<br/>"
        "2. 若有出差前已核准簽呈請註明簽呈代號於出差事由欄位中。<br/>"
        "3. 若為國外差旅申請請註明外幣、換算後台幣及匯率。<br/>"
        "   設算匯率以出國當日台灣銀行兌匯匯率計之，並說明計算式。<br/>"
        "4. 交通費請附相關票根、登機證、旅行社代收轉付收據等憑證。過路費屬其他費用，需附記錄證明。<br/>"
        "5. 膳費及宿費請附發票或收據。"
    )
    story.append(p(notes, c_left))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

# ----------------------------------------------------------------------
# Streamlit 主介面
# ----------------------------------------------------------------------
st.set_page_config(page_title="出差旅費填報系統", page_icon="📝", layout="centered")

current_font = init_chinese_font()

st.title("📝 出差旅費報告單 - 填報系統")

# 1. 報帳模式選擇
st.subheader("📌 報帳模式")
mode = st.radio("請選擇專案模式", ["茶博專案", "高美專案"], horizontal=True)
config = PROJECT_CONFIG[mode]

# 2. 基本資料
st.subheader("👤 基本資料")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("姓名 (可留空供手寫簽名)", value="")
    
    reason_opts = ["茶農拜訪", "農友拜訪", "總部會議", "✍️ 其他 (手動自訂)"]
    def_reason_idx = 0 if config["default_reason"] == "茶農拜訪" else 1
    selected_reason = st.selectbox("出差事由 (參考選單)", reason_opts, index=def_reason_idx)
    if selected_reason == "✍️ 其他 (手動自訂)":
        reason = st.text_input("請輸入自訂出差事由", value="")
    else:
        reason = selected_reason

with col2:
    # 單位及職稱：僅保留對應專案預設單位，移除其他中慈單位
    dept_opts = [config["dept"], "✍️ 其他 (手動自訂)"]
    selected_dept = st.selectbox("單位及職稱 (參考選單)", dept_opts, index=0)
    if selected_dept == "✍️ 其他 (手動自訂)":
        dept = st.text_input("請輸入自訂單位及職稱", value="")
    else:
        dept = selected_dept

    city_opts = config["cities"] + ["✍️ 其他 (手動自訂)"]
    selected_city = st.selectbox("出差國家城市 (參考選單)", city_opts, index=0)
    if selected_city == "✍️ 其他 (手動自訂)":
        city = st.text_input("請輸入自訂出差國家城市", value="")
    else:
        city = selected_city

pay_opts = ["個人", "匯款", "領現金", "✍️ 其他 (手動自訂)"]
selected_pay = st.selectbox("付款方式 (參考選單)", pay_opts, index=0)
if selected_pay == "✍️ 其他 (手動自訂)":
    payment_method = st.text_input("請輸入自訂付款方式", value="")
else:
    payment_method = selected_pay

# 3. 出差時間
st.subheader("📅 出差時間與單據")

today = datetime.date.today()
if 'start_date' not in st.session_state:
    st.session_state.start_date = today
if 'end_date' not in st.session_state:
    st.session_state.end_date = today

def on_start_date_change():
    st.session_state.end_date = st.session_state.start_date

col_d1, col_d2 = st.columns(2)
with col_d1:
    start_date = st.date_input("出差起始日期 (起)", key="start_date", on_change=on_start_date_change)
with col_d2:
    end_date = st.date_input("出差截止日期 (迄)", key="end_date")

calc_days = (end_date - start_date).days + 1
if calc_days < 1:
    calc_days = 1

col_t1, col_t2 = st.columns(2)
with col_t1:
    days = st.text_input("共計天數", value=str(calc_days))
with col_t2:
    receipts = st.text_input("附單據張數", value="1")

roc_y1 = str(start_date.year - 1911)
m1 = str(start_date.month)
d1 = str(start_date.day)

roc_y2 = str(end_date.year - 1911)
m2 = str(end_date.month)
d2 = str(end_date.day)

# 4. 費用明細紀錄
st.subheader("💰 費用明細紀錄")
col_p1, col_p2 = st.columns(2)
with col_p1:
    num_people = st.number_input("出差人數 (人)", min_value=1, max_value=10, value=1, step=1)
with col_p2:
    calc_incidental = st.checkbox("計算每人 400 元雜費", value=True)

if city in config["fares"]:
    info = config["fares"][city]
    single_fare = info["fare"]
    total_transit = single_fare * num_people
    detail_str = f"台中到{info['name']}{info['type']} {single_fare}元(來回)x{num_people}人={total_transit}元"
    standard_route = f"台中到{city}來回"
else:
    total_transit = 0
    detail_str = f"出差至{city}"
    standard_route = f"台中到{city}來回" if city else "台中來回"

total_incidental = (400 * num_people) if calc_incidental else 0

st.info(f"💡 **自動計算預覽**：\n- 大眾交通：**{total_transit} 元** ({standard_route})\n- 雜費金額：**{total_incidental} 元**\n- 洽辦說明：{detail_str}")

if 'exp_rows' not in st.session_state:
    st.session_state.exp_rows = 1

expenses_data = []
for i in range(st.session_state.exp_rows):
    with st.expander(f"費用項目 #{i+1}", expanded=(i==0)):
        col_em, col_ed, col_er = st.columns([1, 1, 2])
        with col_em:
            e_m = st.text_input(f"月份 #{i+1}", value=m1, key=f"em_{i}")
        with col_ed:
            e_d = st.text_input(f"日期 #{i+1}", value=d1, key=f"ed_{i}")
        with col_er:
            def_route = standard_route if i == 0 else ""
            e_route = st.text_input(f"行程 #{i+1}", value=def_route, key=f"er_{i}")

        e_col1, e_col2, e_col3 = st.columns(3)
        with e_col1:
            def_pub = str(total_transit) if (i == 0 and total_transit > 0) else ""
            e_pub = st.text_input(f"大眾交通金額 #{i+1}", value=def_pub, key=f"ep_{i}")
        with e_col2:
            e_desc_opts = ["雜費", "公務車", "過路費", "", "✍️ 其他 (手動自訂)"]
            def_desc_idx = 0 if i == 0 else 3
            e_desc_sel = st.selectbox(f"摘要 #{i+1}", e_desc_opts, index=def_desc_idx, key=f"edesc_sel_{i}")
            if e_desc_sel == "✍️ 其他 (手動自訂)":
                e_desc = st.text_input(f"請輸入自訂摘要 #{i+1}", value="", key=f"edesc_custom_{i}")
            else:
                e_desc = e_desc_sel
        with e_col3:
            def_amt = str(total_incidental) if (i == 0 and total_incidental > 0) else ""
            e_amt = st.text_input(f"雜費金額 #{i+1}", value=def_amt, key=f"eamt_{i}")

        expenses_data.append({
            'm': e_m, 'd': e_d, 'route': e_route,
            'public_trans': e_pub, 'meal': '', 'other_desc': e_desc, 'amount': e_amt
        })

col_eb1, col_eb2 = st.columns(2)
with col_eb1:
    if st.button("➕ 新增一筆費用") and st.session_state.exp_rows < 6:
        st.session_state.exp_rows += 1
        st.rerun()
with col_eb2:
    if st.button("➖ 減少一筆費用") and st.session_state.exp_rows > 1:
        st.session_state.exp_rows -= 1
        st.rerun()

# 5. 出差報告紀錄
st.subheader("📋 出差報告紀錄")
if 'rep_rows' not in st.session_state:
    st.session_state.rep_rows = 1

reports_data = []
for i in range(st.session_state.rep_rows):
    with st.expander(f"洽辦紀錄 #{i+1}", expanded=(i==0)):
        col_rm, col_rd = st.columns(2)
        with col_rm:
            r_m = st.text_input(f"報告月份 #{i+1}", value=m1, key=f"rm_{i}")
        with col_rd:
            r_d = st.text_input(f"報告日期 #{i+1}", value=d1, key=f"rd_{i}")

        r_target = st.text_area(f"接洽人員 (可換行輸入多個單位)", height=3, key=f"rt_{i}")
        def_detail = detail_str if i == 0 else ""
        r_detail = st.text_input(f"洽辦事項說明 #{i+1}", value=def_detail, key=f"rdet_{i}")

        reports_data.append({
            'm': r_m, 'd': r_d, 'target': r_target, 'detail': r_detail
        })

col_rb1, col_rb2 = st.columns(2)
with col_rb1:
    if st.button("➕ 新增一筆報告") and st.session_state.rep_rows < 3:
        st.session_state.rep_rows += 1
        st.rerun()
with col_rb2:
    if st.button("➖ 減少一筆報告") and st.session_state.rep_rows > 1:
        st.session_state.rep_rows -= 1
        st.rerun()

st.markdown("---")
form_data = {
    'name': name,
    'dept': dept,
    'reason': reason,
    'city': city,
    'payment_method': payment_method,
    'y1': roc_y1, 'm1': m1, 'd1': d1,
    'y2': roc_y2, 'm2': m2, 'd2': d2,
    'days': days, 'receipts': receipts,
    'expenses': expenses_data,
    'reports': reports_data
}

pdf_bytes = generate_pdf_bytes(form_data, current_font)
export_filename = f"{start_date.strftime('%Y%m%d')}_出差報告單.pdf"

b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
download_html = f'''
    <a href="data:application/pdf;base64,{b64_pdf}" download="{export_filename}" target="_blank" style="
        display: block;
        width: 100%;
        text-align: center;
        background-color: #1f4e78;
        color: white;
        padding: 14px 0px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 8px;
        text-decoration: none;
        margin-top: 10px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.2);
    ">📄 產生並下載出差報告單 PDF ({export_filename})</a>
'''

st.markdown(download_html, unsafe_allow_html=True)
