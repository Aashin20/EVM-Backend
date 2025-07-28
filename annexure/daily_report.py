from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from typing import List, Dict
import uuid

def daily_report(district_data: List[Dict]):
    # Kerala districts
    kerala_districts_short = [
        "TVM", "KLM", "PTM", "ALP",
        "KTM", "IDK", "EKM", "TSR", "PKD",
        "MLP", "KHZ", "WYD", "KNR", "KSR"
    ]
    kerala_districts = [
        "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha",
        "Kottayam", "Idukki", "Ernakulam", "Thrissur", "Palakkad",
        "Malappuram", "Kozhikode", "Wayanad", "Kannur", "Kasaragod"
    ]

    print(district_data, flush=True)

    # Create document - landscape orientation
    filename = f"Daily_report{uuid.uuid4().hex[:8]}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4),
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=10,
        spaceAfter=4
    )
    header_label_style = ParagraphStyle(
        'HeaderLabel',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=9,
        textColor=colors.gray
    )
    header_value_style = ParagraphStyle(
        'HeaderValue',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=10,
        leading=12
    )

    # Content elements
    elements = []

    # Logo
    try:
        logo = Image("annexure/logo.png", width=0.8*inch, height=0.8*inch)
        logo.hAlign = 'CENTER'
        elements.append(logo)
    except:
        elements.append(Paragraph("LOGO", title_style))

    elements.append(Spacer(1, 8))

    # Main Heading
    heading = Paragraph("Daily progress report of FLC of EVMs", title_style)
    elements.append(heading)

    elements.append(Spacer(1, 10))

    # Current date
    current_date = datetime.now().strftime("%d-%m-%Y")

    # Date header
    date_header_info = [
        [Paragraph("Date", header_label_style)],
        [Paragraph(current_date, header_value_style)]
    ]

    date_header_table = Table(date_header_info, colWidths=[200])
    date_header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
    ]))
    elements.append(date_header_table)

    elements.append(Spacer(1, 20))

    # Headers
    headers = [
        ["District", "No. of EVMs checked till date", "", "", "", "", "", "No. of EVMs checked on the date", "", "", "", "", "", "Total", "", "", "", "", ""],
        ["", "CU", "", "", "BU", "", "", "CU", "", "", "BU", "", "", "CU", "", "", "BU", "", ""],
        ["", "Pass", "Fail", "Total", "Pass", "Fail", "Total", "Pass", "Fail", "Total", "Pass", "Fail", "Total", "Pass", "Fail", "Total", "Pass", "Fail", "Total"]
    ]
    table_data = headers.copy()

    # Create lookup dictionary
    data_dict = {}
    for data_row in district_data:
        district = data_row.get('district', '')
        data_dict[district] = data_row

    # Add data rows for each district
    for district in kerala_districts:
        short_form = kerala_districts_short[kerala_districts.index(district)]

        data_row = data_dict.get(district, {})
        cu_till_pass = data_row.get('cu_till_pass', 0)
        cu_till_fail = data_row.get('cu_till_fail', 0)
        cu_till_total = cu_till_pass + cu_till_fail
        bu_till_pass = data_row.get('bu_till_pass', 0)
        bu_till_fail = data_row.get('bu_till_fail', 0)
        bu_till_total = bu_till_pass + bu_till_fail

        cu_on_pass = data_row.get('cu_on_pass', 0)
        cu_on_fail = data_row.get('cu_on_fail', 0)
        cu_on_total = cu_on_pass + cu_on_fail
        bu_on_pass = data_row.get('bu_on_pass', 0)
        bu_on_fail = data_row.get('bu_on_fail', 0)
        bu_on_total = bu_on_pass + bu_on_fail

        cu_grand_pass = cu_till_pass + cu_on_pass
        cu_grand_fail = cu_till_fail + cu_on_fail
        cu_grand_total = cu_grand_pass + cu_grand_fail
        bu_grand_pass = bu_till_pass + bu_on_pass
        bu_grand_fail = bu_till_fail + bu_on_fail
        bu_grand_total = bu_grand_pass + bu_grand_fail

        row = [
            short_form,
            str(cu_till_pass), str(cu_till_fail), str(cu_till_total),
            str(bu_till_pass), str(bu_till_fail), str(bu_till_total),
            str(cu_on_pass), str(cu_on_fail), str(cu_on_total),
            str(bu_on_pass), str(bu_on_fail), str(bu_on_total),
            str(cu_grand_pass), str(cu_grand_fail), str(cu_grand_total),
            str(bu_grand_pass), str(bu_grand_fail), str(bu_grand_total)
        ]
        table_data.append(row)

    # Table and styling
    col_widths = [60, 35, 35, 35, 35, 35, 35, 35, 35, 35, 35, 35, 35, 35, 35, 35, 35, 35, 35]
    main_table = Table(table_data, colWidths=col_widths)
    table_style = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 2), colors.lightgrey),

        # Header cell spans
        ('SPAN', (1, 0), (6, 0)),
        ('SPAN', (7, 0), (12, 0)),
        ('SPAN', (13, 0), (18, 0)),

        ('SPAN', (1, 1), (3, 1)),
        ('SPAN', (4, 1), (6, 1)),
        ('SPAN', (7, 1), (9, 1)),
        ('SPAN', (10, 1), (12, 1)),
        ('SPAN', (13, 1), (15, 1)),
        ('SPAN', (16, 1), (18, 1)),

        ('SPAN', (0, 0), (0, 2)),
    ]
    main_table.setStyle(TableStyle(table_style))
    elements.append(main_table)

    # Build document
    doc.build(elements)
    return filename
