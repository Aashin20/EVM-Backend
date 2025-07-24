from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from typing import List, Dict
import uuid

def appendix_1(daily_data: List[Dict], district: str):
    # Create document - landscape orientation
    filename = f"Appendix_1_{uuid.uuid4().hex[:8]}.pdf"
    
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4), 
                          leftMargin=0.75*inch, rightMargin=0.75*inch, 
                          topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=12,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=10,
        spaceAfter=12
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
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER
    )
    
    # Content elements
    elements = []
    
    # Logo
    try:
        logo = Image("annexure/logo.png", width=1*inch, height=1*inch)
        logo.hAlign = 'CENTER'
        elements.append(logo)
    except:
        elements.append(Paragraph("LOGO", title_style))
    
    elements.append(Spacer(1, 12))
    
    # Title
    title = Paragraph("Appendix - I", title_style)
    elements.append(title)
    
    elements.append(Spacer(1, 12))
    
    # Main Heading
    heading = Paragraph("Daily progress report of FLC of EVMs", title_style)
    elements.append(heading)
    
    elements.append(Spacer(1, 15))
    
    # Current date
    current_date = datetime.now().strftime("%d-%m-%Y")
    
    # Horizontal header info
    header_info = [
        [Paragraph("District", header_label_style),
         Paragraph("Date", header_label_style)],
        [Paragraph(district, header_value_style),
         Paragraph(current_date, header_value_style)]
    ]
    
    header_table = Table(header_info, colWidths=[200, 200])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
    ]))
    elements.append(header_table)
    
    elements.append(Spacer(1, 30))
    
    # Create table headers - properly structured for merged cells
    headers = [
        ["Date", "No. of EVMs checked till\ndate", "", "No. of EVMs checked on\nthe date", "", "Total", "", "Remarks"],
        ["", "CU", "BU", "CU", "BU", "CU", "BU", ""]
    ]
    
    # Table data starting with headers
    table_data = headers.copy()
    
    # Add data rows
    for data_row in daily_data:
        date = str(data_row.get('date', ''))
        cu_till = data_row.get('cu_till_date', 0)
        bu_till = data_row.get('bu_till_date', 0)
        cu_on = data_row.get('cu_on_date', 0)
        bu_on = data_row.get('bu_on_date', 0)
        remarks = str(data_row.get('remarks', ''))
        
        # Calculate totals
        cu_total = cu_till + cu_on
        bu_total = bu_till + bu_on
        
        row = [
            date,
            str(cu_till),
            str(bu_till),
            str(cu_on),
            str(bu_on),
            str(cu_total),
            str(bu_total),
            remarks
        ]
        table_data.append(row)
    
    # Set column widths
    col_widths = [60, 80, 80, 80, 80, 80, 80, 80]
    
    # Create table
    main_table = Table(table_data, colWidths=col_widths)
    
    # Table styling
    table_style = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),  # Header rows background
        
        # Merge cells for main headers
        ('SPAN', (1, 0), (2, 0)),  # "No. of EVMs checked till date"
        ('SPAN', (3, 0), (4, 0)),  # "No. of EVMs checked on the date"  
        ('SPAN', (5, 0), (6, 0)),  # "Total"
        ('SPAN', (0, 0), (0, 1)),  # "Date" spans 2 rows
        ('SPAN', (7, 0), (7, 1)),  # "Remarks" spans 2 rows
    ]
    
    main_table.setStyle(TableStyle(table_style))
    elements.append(main_table)
    
    # Add signature section
    elements.append(Spacer(1, 60))
    
    signature_style_centered = ParagraphStyle(
        'SignatureCentered',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        leading=12
    )
    
    # Signature texts
    sig_text1 = "Signature of FLC Charge Officer"
    sig_text2 = "Signature of DEO"
    
    # Signature table with proper spacing
    sig_data = [
        [Paragraph(sig_text1, signature_style_centered), "", Paragraph(sig_text2, signature_style_centered)]
    ]
    
    sig_table = Table(sig_data, colWidths=[250, 200, 250])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(sig_table)
    
    # Build document
    doc.build(elements)
    return filename