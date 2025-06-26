from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class CUReturn(BaseModel):
    cu_no: str
    bu_no: int
    dmm_no_return: str
    dmm_no_treasury: str


def Return_RO_BO(details: List[CUReturn], RO:str,alloted_to: str, DOP:str,DOC:str, filename="Annexure_11.pdf"):
    # Create document
    doc = SimpleDocTemplate(filename, pagesize=A4, 
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
    title = Paragraph("Annexure - XI", title_style)
    elements.append(title)
    
    # Reference
    reference = Paragraph("(See Para 4.1 (c) of Chapter 4)", subtitle_style)
    elements.append(reference)
    
    # Main Heading
    heading = Paragraph("Register for return of EVM from Returning Officer to Block Panchayat Secretary/ERO of Municipality ", title_style)
    elements.append(heading)
    
    elements.append(Spacer(1, 15))
    
    # Current date
    current_date = datetime.now().strftime("%d-%m-%Y")
    
    # Horizontal header info
    header_info = [
         [Paragraph("Returning Officer of", header_label_style),
         Paragraph("Date of Poll", header_label_style),
         Paragraph("Date of Counting", header_label_style),
         Paragraph("Returned to", header_label_style),
         Paragraph("Date of Return", header_label_style)
         ],
        [Paragraph(RO, header_value_style),
         Paragraph(DOP, header_value_style),
         Paragraph(DOC, header_value_style), 
         Paragraph(alloted_to, header_value_style),
         Paragraph(current_date, header_value_style)
         ]
    ]
    
    header_table = Table(header_info, colWidths=[120, 120, 120])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
    ]))
    elements.append(header_table)
    
    elements.append(Spacer(1, 30))
    
    
    
    # Column headers
    headers = [
        "SI No.", 
        "CU No.", 
        "BU No", 
        "DMM No. (Returned)",
        "DMM No. (In Treasury)"
    ]
    
    # Column index headers
    index_headers = ["1", "2", "3", "4", "5"]
    
    # Component table data
    comp_data = [headers, index_headers]
    
    # Add component rows
    for i, comp in enumerate(details):
       
        
        comp_data.append([
            str(i+1), 
            comp.cu_no,
            comp.bu_no,
            comp.dmm_no_return,
            comp.dmm_no_treasury
        ])
    
    # Add Total Count row directly after the data (no empty rows)
    comp_data.append(["Total Count", str(len(details)), "", "", ""])
    
    # Set column widths for 5 columns
    col_widths = [60, 100, 100, 120, 120]
    
    comp_table = Table(comp_data, colWidths=col_widths)
    comp_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Center headers
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),  # Center index row
        ('ALIGN', (0, 2), (0, -2), 'CENTER'),  # Center SI No. column
        ('ALIGN', (1, 2), (-1, -2), 'CENTER'),  # Center data cells
        ('ALIGN', (0, -1), (0, -1), 'LEFT'),   # Left-align "Total Count"
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),  # Index row background
    ]))
    elements.append(comp_table)
    
    # Add signature section only at the end
    elements.append(Spacer(1, 60))
    
    signature_style_centered = ParagraphStyle(
    'SignatureCentered',
    parent=styles['Normal'],
    fontSize=10,
    alignment=TA_CENTER,
    leading=12
    )

    # Combine both lines as a centered block
    sig_text1 = "Signature, Name & Designation<br/>of Officer Handing over"
    sig_text2 = "Signature, Name & Designation<br/>of Officer Taking over"

    # Centered Paragraphs in left/right cells
    sig_data = [
        [Paragraph(sig_text1, signature_style_centered), "", Paragraph(sig_text2, signature_style_centered)]
    ]

    sig_table = Table(sig_data, colWidths=[180, 160, 180])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(sig_table)
            
    # Build document
    doc.build(elements)
    return filename
