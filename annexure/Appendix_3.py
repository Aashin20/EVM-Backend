from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from typing import List, Dict
import uuid

def appendix_3(joining_date: str, members: List[str], evm_data: Dict, 
               free_accommodation: bool, local_conveyance: bool, 
               relieving_date: str):
    
    # Create document - portrait orientation
    filename = f"Appendix_3_{uuid.uuid4().hex[:8]}.pdf"

    doc = SimpleDocTemplate(filename, pagesize=A4, 
                          leftMargin=0.75*inch, rightMargin=0.75*inch, 
                          topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=14,
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=12,
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_LEFT,
        spaceAfter=6,
        leading=14
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeaderStyle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_LEFT,
        spaceAfter=8,
        fontName='Helvetica-Bold'
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
    
    elements.append(Spacer(1, 20))
    
    # Title
    title = Paragraph("Appendix - III", title_style)
    elements.append(title)
    
    elements.append(Spacer(1, 15))
    
    # Certificate heading
    cert_heading = Paragraph("<u>CERTIFICATE</u>", subtitle_style)
    elements.append(cert_heading)
    
    elements.append(Spacer(1, 20))
    
    # Main text
    main_text = ("This is to certify the the team of ECIL Engineers consisting of the following members have reported at "
                f"this office on <u>{joining_date}</u> for First Level Checking of Electronic Voting Machines.")
    main_para = Paragraph(main_text, normal_style)
    elements.append(main_para)
    
    elements.append(Spacer(1, 15))
    
    section_a = Paragraph("(a)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Members of the team", section_header_style)
    elements.append(section_a)

    elements.append(Spacer(1, 8))

    # Members list (only list actual entries)
    for i, member in enumerate(members, 1):
        if member.strip():  # Only add non-empty members
            member_text = f"{i}. {member}"
        else:
            member_text = f"{i}. Sri......................."
        member_para = Paragraph(member_text, normal_style)
        elements.append(member_para)
        
        elements.append(Spacer(1, 0))
    
    # Section (b) - Abstract of the result of First Level Check
    section_b = Paragraph("(b)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Abstract of the result of First Level Check", section_header_style)
    elements.append(section_b)
    
    elements.append(Spacer(1, 10))
    
    # Create EVM results table
    evm_table_data = [
        ["Total No. of EVMs tested", "", "No. of EVMs passed in testing", "", "No. of EVMs rejected", ""],
        ["CU", "BU", "CU", "BU", "CU", "BU"],
        [
            str(evm_data.get('cu_tested', '')),
            str(evm_data.get('bu_tested', '')),
            str(evm_data.get('cu_passed', '')),
            str(evm_data.get('bu_passed', '')),
            str(evm_data.get('cu_rejected', '')),
            str(evm_data.get('bu_rejected', ''))
        ]
    ]
    
    # Column widths for EVM table
    evm_col_widths = [70, 70, 70, 70, 70, 70]
    
    evm_table = Table(evm_table_data, colWidths=evm_col_widths)
    evm_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
        ('SPAN', (0, 0), (1, 0)),  # "Total No. of EVMs tested"
        ('SPAN', (2, 0), (3, 0)),  # "No. of EVMs passed in testing"
        ('SPAN', (4, 0), (5, 0)),  # "No. of EVMs rejected"
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(evm_table)
    
    elements.append(Spacer(1, 20))
    
    # Section (c) - Whether the ECIL Engineers have been provided with
    section_c = Paragraph("(c)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Whether the ECIL Engineers have been provided with :", section_header_style)
    elements.append(section_c)
    
    elements.append(Spacer(1, 10))
    
    # Accommodation and conveyance
    accommodation_text = f"(i) Free Accommodation&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{'Yes' if free_accommodation else 'No'}"
    accommodation_para = Paragraph(accommodation_text, normal_style)
    elements.append(accommodation_para)
    
    conveyance_text = f"(ii) Local Conveyance&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{'Yes' if local_conveyance else 'No'}"
    conveyance_para = Paragraph(conveyance_text, normal_style)
    elements.append(conveyance_para)
    
    elements.append(Spacer(1, 20))
    
    # Section (d) - The ECIL Team has been relieved on
    section_d = Paragraph(f"(d)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The ECIL Team has been relieved on <u>{relieving_date}</u>", section_header_style)
    elements.append(section_d)
    
    elements.append(Spacer(1, 30))
    
    # Signature section
    signature_table_data = [
        ["Station :", "", "Signature of Authorised Officer"],
        ["Dated :", "", "(Stamp)"],
        ["", "(Seal of Collectorate)", ""]
    ]
    
    signature_table = Table(signature_table_data, colWidths=[100, 200, 180])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('ALIGN', (1, 2), (1, 2), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(signature_table)
    
    # Build document
    doc.build(elements)
    return filename