from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import uuid

class EVMPair(BaseModel):
    cu_no: str
    dmm_no: str
    bu_nos: List[str]


def create_page_content(pair: EVMPair, pair_index: int):
    """Create content for a single page/EVM pair"""
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=14,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=10,
        spaceAfter=12
    )
    form_title_style = ParagraphStyle(
        'FormTitleStyle',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=12,
        spaceAfter=15,
        fontName='Helvetica-Bold'
    )
    field_style = ParagraphStyle(
        'FieldStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        leading=14
    )
    
    # Content elements for this page
    page_elements = []
    
    # Logo
    try:
        logo = Image("annexure/logo.png", width=1*inch, height=1*inch)
        logo.hAlign = 'CENTER'
        page_elements.append(logo)
    except:
        page_elements.append(Paragraph("LOGO", title_style))
    
    page_elements.append(Spacer(1, 12))
    
    # Form Number
    form_number = Paragraph("Form N-36", title_style)
    page_elements.append(form_number)
    
    # Reference
    reference = Paragraph("(See para 2.5 (d) of Chapter 2)", subtitle_style)
    page_elements.append(reference)
    
    # Main Title
    main_title = Paragraph("Receipt of return of EVMs", form_title_style)
    page_elements.append(main_title)
    
    page_elements.append(Spacer(1, 20))
    
    # Current date and time field
    page_elements.append(Paragraph(f"I, {'.' * 95} (Name and official address of warehouse incharge) have received the following EVMs from  {'.' * 65} at {'.' * 18} (time) on {'.' * 15} (date).", field_style))
    
    page_elements.append(Spacer(1, 25))
    
    # Main table headers
    headers = ["Sl No.", "CU No.", "DMM No.", "BU No."]
    
    # Create table data for this specific pair
    table_data = [headers]
    
    row_counter = 1
    total_cu_count = 1  # Each page has exactly 1 CU
    total_dmm_count = 1  # Each page has exactly 1 DMM
    total_bu_count = len(pair.bu_nos)
    
    # Process the current EVM pair
    if pair.bu_nos:  # If there are BUs in this pair
        # First row of the pair - contains CU, DMM, and first BU
        first_row = [str(row_counter), pair.cu_no, pair.dmm_no, pair.bu_nos[0]]
        table_data.append(first_row)
        row_counter += 1
        
        # Subsequent rows for remaining BUs - CU and DMM columns empty
        for bu_no in pair.bu_nos[1:]:
            subsequent_row = [str(row_counter), "", "", bu_no]
            table_data.append(subsequent_row)
            row_counter += 1
    else:
        # If no BUs, just add CU and DMM
        row = [str(row_counter), pair.cu_no, pair.dmm_no, ""]
        table_data.append(row)
        row_counter += 1
    
    # Add empty rows to reach minimum 10 rows if needed
    while len(table_data) - 1 < 10:  # -1 because first row is header
        empty_row = [str(row_counter), "", "", ""]
        table_data.append(empty_row)
        row_counter += 1
    
    # Add Total Count row
    total_row = ["Total Count", str(total_cu_count), str(total_dmm_count), str(total_bu_count)]
    table_data.append(total_row)
    
    # Set column widths
    col_widths = [80, 140, 140, 140]
    
    main_table = Table(table_data, colWidths=col_widths)
    main_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background only
    ]))
    page_elements.append(main_table)
    
    # Add signature section
    page_elements.append(Spacer(1, 50))
    
    signature_style = ParagraphStyle(
        'SignatureStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        leading=12
    )

    # Signature texts
    sig_text1 = "Signature, Name & Designation of<br/>Officer Handing over"
    sig_text2 = "Signature, Name & Designation of<br/>Officer Taking over"

    # Signature table
    sig_data = [
        [Paragraph(sig_text1, signature_style), "", Paragraph(sig_text2, signature_style)]
    ]

    sig_table = Table(sig_data, colWidths=[200, 100, 200])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    page_elements.append(sig_table)
    
    return page_elements


def Form_N36(evm_pairs: List[EVMPair], allotment_order_no: str):

    filename = f"Form_N36_{uuid.uuid4().hex[:8]}.pdf"
    
    doc = SimpleDocTemplate(filename, pagesize=A4, 
                          leftMargin=0.75*inch, rightMargin=0.75*inch, 
                          topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # All content elements for the entire document
    all_elements = []
    
    # Process each EVM pair and create a separate page
    for i, pair in enumerate(evm_pairs):
        # Get page content for this pair
        page_content = create_page_content(pair, i)
        
        # Add all page content to the document
        all_elements.extend(page_content)
        
        # Add page break after each pair except the last one
        if i < len(evm_pairs) - 1:
            all_elements.append(PageBreak())
    
    # Build document
    doc.build(all_elements)
    return filename
