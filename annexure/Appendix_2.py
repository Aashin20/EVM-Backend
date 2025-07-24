from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from typing import List, Dict
import uuid
import tempfile
import os

def appendix_2(flc_data: List[Dict], district: str):
    # Create document - landscape orientation

    filename = f"Appendix_2_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(tempfile.gettempdir(), filename)

    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4), 
                          leftMargin=0.75*inch, rightMargin=0.75*inch, 
                          topMargin=0.75*inch, bottomMargin=0.75*inch)
    completion_date = datetime.now().strftime('%Y-%m-%d')
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
    
    # Remarks cell style with left alignment for better readability
    remarks_style = ParagraphStyle(
        'RemarksStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        leading=12,
        leftIndent=3,
        rightIndent=3
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
    title = Paragraph("Appendix - II", title_style)
    elements.append(title)
    
    elements.append(Spacer(1, 12))
    
    # Main Heading
    heading = Paragraph("Abstract of FLC results", title_style)
    elements.append(heading)
    
    elements.append(Spacer(1, 15))
    
    # Horizontal header info
    header_info = [
        [Paragraph("District :", header_label_style),
         Paragraph("Date of completion of FLC :", header_label_style)],
        [Paragraph(district, header_value_style),
         Paragraph(completion_date, header_value_style)]
    ]
    
    header_table = Table(header_info, colWidths=[200, 250])
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
        ["Total No. of EVMs\nsubjected to FLC", "", "No. of EVMs passed in FLC", "", "No. of EVMs failed in FLC", "", "Pass percentage", "", "Remarks"],
        ["CU", "BU", "CU", "BU", "CU", "BU", "CU", "BU", ""]
    ]
    
    # Table data starting with headers
    table_data = headers.copy()
    
    # Add data rows
    for data_row in flc_data:
        cu_total = data_row.get('cu_total', 0)
        bu_total = data_row.get('bu_total', 0)
        cu_passed = data_row.get('cu_passed', 0)
        bu_passed = data_row.get('bu_passed', 0)
        cu_failed = data_row.get('cu_failed', 0)
        bu_failed = data_row.get('bu_failed', 0)
        
        # Calculate pass percentages
        cu_percentage = round((cu_passed / cu_total * 100), 2) if cu_total > 0 else 0
        bu_percentage = round((bu_passed / bu_total * 100), 2) if bu_total > 0 else 0
        
        remarks = str(data_row.get('remarks', ''))
        
        # Wrap remarks in Paragraph for automatic text wrapping
        remarks_para = Paragraph(remarks, remarks_style)
        
        row = [
            str(cu_total),
            str(bu_total),
            str(cu_passed),
            str(bu_passed),
            str(cu_failed),
            str(bu_failed),
            str(cu_percentage),
            str(bu_percentage),
            remarks_para  # Use Paragraph instead of plain string
        ]
        table_data.append(row)
    
    # Set column widths - making remarks column wider and flexible
    col_widths = [60, 80, 80, 60, 60, 60, 60, 60, 150]
    
    # Create table with dynamic row heights
    main_table = Table(table_data, colWidths=col_widths, repeatRows=2)
    
    # Table styling with dynamic row heights
    table_style = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),  # Header rows background
        ('LEFTPADDING', (8, 2), (8, -1), 6),  # Left padding for remarks column
        ('RIGHTPADDING', (8, 2), (8, -1), 6),  # Right padding for remarks column
        ('TOPPADDING', (0, 0), (-1, -1), 6),   # Top padding for all cells
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6), # Bottom padding for all cells
        
        # Merge cells for main headers
        ('SPAN', (0, 0), (1, 0)),  # "Total No. of EVMs subjected to FLC"
        ('SPAN', (2, 0), (3, 0)),  # "No. of EVMs passed in FLC"  
        ('SPAN', (4, 0), (5, 0)),  # "No. of EVMs failed in FLC"
        ('SPAN', (6, 0), (7, 0)),  # "Pass percentage"
        ('SPAN', (8, 0), (8, 1)),  # "Remarks" spans 2 rows
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
    file_size = os.path.getsize(filepath)
    return filepath  
