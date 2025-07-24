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


def create_page_content(evm_pair: EVMPair, allotment_order_no: str, styles: dict, page_number: int, total_pages: int) -> List:
    """Create content for a single page"""
    elements = []
    
    # Logo
    try:
        logo = Image("annexure/logo.png", width=1*inch, height=1*inch)
        logo.hAlign = 'CENTER'
        elements.append(logo)
    except:
        elements.append(Paragraph("LOGO", styles['title_style']))
    
    elements.append(Spacer(1, 12))
    
    # Form Number
    form_number = Paragraph("Form N-35", styles['title_style'])
    elements.append(form_number)
    
    # Reference
    reference = Paragraph("(See para 2.5 (c) of Chapter 2)", styles['subtitle_style'])
    elements.append(reference)
    
    # Main Title
    main_title = Paragraph("Acknowledgement of receipt of EVMs", styles['form_title_style'])
    elements.append(main_title)
    
    # Page number
    page_info = Paragraph(f"Page {page_number} of {total_pages}", styles['subtitle_style'])
    elements.append(page_info)
    
    elements.append(Spacer(1, 20))
    
    # Current date and time
    current_datetime = datetime.now()
    current_date = current_datetime.strftime("%d-%m-%Y")
    current_time = current_datetime.strftime("%H:%M")
    
    # Header fields - First row with Allotment Order and Date
    first_row_data = [
        [Paragraph(f"Allotment Order No: {allotment_order_no}", styles['field_style']), 
         Paragraph(f"Date: {current_date}", styles['field_style'])]
    ]
    
    first_row_table = Table(first_row_data, colWidths=[400, 120])
    first_row_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(first_row_table)
    
    # Other fields - single column spanning full width
    elements.append(Paragraph(f"Purpose of movement {'.' * 85}", styles['field_style']))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Whether movement is {'.' * 85}", styles['field_style']))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"I, {'.' * 95} (Name and official address of the receiving officer) have received the following EVMs from the officer incharge of {'.' * 65} warehouse at {'.' * 18} (time) on {'.' * 15} (date).", styles['field_style']))
    
    elements.append(Spacer(1, 25))
    
    # Main table headers
    headers = ["Sl No.", "CU No.", "DMM No.", "BU No."]
    
    # Create table data for this specific EVM pair
    table_data = [headers]
    
    row_counter = 1
    total_cu_count = 1  # Each page has exactly 1 CU
    total_dmm_count = 1  # Each page has exactly 1 DMM
    total_bu_count = len(evm_pair.bu_nos)
    
    # Process the single EVM pair for this page
    if evm_pair.bu_nos:  # If there are BUs in this pair
        # First row of the pair - contains CU, DMM, and first BU
        first_row = [str(row_counter), evm_pair.cu_no, evm_pair.dmm_no, evm_pair.bu_nos[0]]
        table_data.append(first_row)
        row_counter += 1
        
        # Subsequent rows for remaining BUs - CU and DMM columns empty
        for bu_no in evm_pair.bu_nos[1:]:
            subsequent_row = [str(row_counter), "", "", bu_no]
            table_data.append(subsequent_row)
            row_counter += 1
    else:
        # If no BUs, just add CU and DMM
        row = [str(row_counter), evm_pair.cu_no, evm_pair.dmm_no, ""]
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
    elements.append(main_table)
    
    # Add signature section
    elements.append(Spacer(1, 50))
    
    # Signature texts
    sig_text1 = "Signature, Name & Designation of<br/>Officer Handing over"
    sig_text2 = "Signature, Name & Designation of<br/>Officer Taking over"

    # Signature table
    sig_data = [
        [Paragraph(sig_text1, styles['signature_style']), "", Paragraph(sig_text2, styles['signature_style'])]
    ]

    sig_table = Table(sig_data, colWidths=[200, 100, 200])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(sig_table)
    
    return elements


def Form_N35(evm_pairs: List[EVMPair], allotment_order_no: str):
    
    filename = f"Form_N35_{uuid.uuid4().hex[:8]}.pdf"

    doc = SimpleDocTemplate(filename, pagesize=A4, 
                          leftMargin=0.75*inch, rightMargin=0.75*inch, 
                          topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Styles
    styles_sheet = getSampleStyleSheet()
    styles = {
        'title_style': ParagraphStyle(
            'TitleStyle',
            parent=styles_sheet['Heading1'],
            alignment=TA_CENTER,
            fontSize=14,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ),
        'subtitle_style': ParagraphStyle(
            'SubtitleStyle',
            parent=styles_sheet['Normal'],
            alignment=TA_CENTER,
            fontSize=10,
            spaceAfter=12
        ),
        'form_title_style': ParagraphStyle(
            'FormTitleStyle',
            parent=styles_sheet['Normal'],
            alignment=TA_CENTER,
            fontSize=12,
            spaceAfter=15,
            fontName='Helvetica-Bold'
        ),
        'field_style': ParagraphStyle(
            'FieldStyle',
            parent=styles_sheet['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            leading=14
        ),
        'signature_style': ParagraphStyle(
            'SignatureStyle',
            parent=styles_sheet['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            leading=12
        )
    }
    
    # Content elements
    elements = []
    total_pages = len(evm_pairs)
    
    # Create a page for each EVM pair
    for i, evm_pair in enumerate(evm_pairs, 1):
        # Create content for this page
        page_elements = create_page_content(evm_pair, allotment_order_no, styles, i, total_pages)
        elements.extend(page_elements)
        
        # Add page break if not the last page
        if i < len(evm_pairs):
            elements.append(PageBreak())
    
    # Build document
    doc.build(elements)
    return filename

