from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class EVMDetail(BaseModel):
    evm_no: str
    constituency_ward_no: str
    polling_station_no: str
    control_unit_no: str
    dmm_no: str
    bu_nos: List[str]
    bu_pink_paper_seal_nos: List[str]

def EVM_Distribution(details: List[EVMDetail], district: str,local_body:str,RO: str,strongroom:str, filename="Annexure_8.pdf"):

    doc = SimpleDocTemplate(filename, pagesize=landscape(A4), 
                          leftMargin=0.5*inch, rightMargin=0.5*inch, 
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
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
        fontSize=8,
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
    title = Paragraph("Annexure - VIII", title_style)
    elements.append(title)
    
    # Reference
    reference = Paragraph("(See Para 4.2   of Chapter 4, 5.3 (a) & (b) of Chapter 5 & 6.4(b) (4) of Chapter 6)", subtitle_style)
    elements.append(reference)
    
    # Main Heading
    heading = Paragraph("Register for Allocation & Distribution and receipt of EVM from Returning Officers to Presiding Officers and back ", title_style)
    elements.append(heading)
    
    elements.append(Spacer(1, 15))
    
    # Current date
    current_date = datetime.now().strftime("%d-%m-%Y")
    
    # Horizontal header info
    header_info = [
         [Paragraph("District", header_label_style),
        Paragraph("Name of G.P/Mun/Cor", header_label_style),
         Paragraph("Returning Officer", header_label_style),
         Paragraph("Date of EVM Commissioning", header_label_style),
        Paragraph("Strongroom", header_label_style)],
        [Paragraph(district, header_value_style),
        Paragraph(local_body, header_value_style),
         Paragraph(RO, header_value_style),
         Paragraph(current_date, header_value_style),
        Paragraph(strongroom, header_value_style), ]
    ]
    
    header_table = Table(header_info, colWidths=[120, 120, 120, 120])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
    ]))
    elements.append(header_table)
    
    elements.append(Spacer(1, 20))
    
    # Main table headers - split into two sections as shown in image
    # Left section: Distribution to the Presiding Officer
    left_headers = [
        [Paragraph("Sl. No.<br/>(EVM No.)", cell_style), "", Paragraph("Distribution to the Presiding Officer", cell_style), "", "", "", "", "", "", Paragraph("Receipt of EVM from<br/>Presiding Officer", cell_style), ""],
        ["", Paragraph("Date of<br/>Issue", cell_style), Paragraph("Constituency/<br/>Ward No.", cell_style), Paragraph("Polling<br/>Station No.", cell_style), Paragraph("Control Unit<br/>No.", cell_style), Paragraph("DMM No.", cell_style), Paragraph("BU No. (s)", cell_style), Paragraph("Bu Pink<br/>Paper<br/>Seal No.<br/>(s)", cell_style), Paragraph("Signature,<br/>Name &<br/>Designation<br/>of Presiding<br/>officer<br/>receiving<br/>the EVM", cell_style), Paragraph("Date &<br/>Time of<br/>receipt", cell_style), Paragraph("Name &<br/>Designation<br/>Sign. Of the<br/>RO/Officer<br/>receiving<br/>back the<br/>EVM", cell_style)],
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
    ]
    
    # Add data rows
    table_data = left_headers.copy()
    
    for i, detail in enumerate(details):
        # Join multiple BU numbers and seal numbers with line breaks
        bu_numbers = "<br/>".join(detail.bu_nos)
        seal_numbers = "<br/>".join(detail.bu_pink_paper_seal_nos)
        
        table_data.append([
            str(i+1),
            current_date,
            detail.constituency_ward_no,
            detail.polling_station_no,
            detail.control_unit_no,
            detail.dmm_no,
            Paragraph(bu_numbers, cell_style),
            Paragraph(seal_numbers, cell_style),
            "", # Signature column - kept blank
            "", # Date & Time column - kept blank  
            ""  # Name & Designation column - kept blank
        ])
    
    # Add Total Count row
    table_data.append(["Total Count", str(len(details)), "", "", "", "", "", "", "", "", ""])
    
    # Set column widths for landscape orientation
    col_widths = [50, 60, 70, 70, 70, 70, 60, 70, 80, 70, 80]
    
    main_table = Table(table_data, colWidths=col_widths)
    main_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # First header row
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),  # Second header row
        ('BACKGROUND', (0, 2), (-1, 2), colors.lightgrey),  # Index row
        # Merge cells for main headers
        ('SPAN', (0, 0), (0, 1)),  # Sl. No. spans 2 rows
        ('SPAN', (2, 0), (8, 0)),  # Distribution header spans columns 3-9
        ('SPAN', (9, 0), (10, 0)), # Receipt header spans columns 10-11
        ('ALIGN', (0, -1), (0, -1), 'LEFT'),   # Left-align "Total Count"
    ]))
    elements.append(main_table)
    
    # Add signature section
    elements.append(Spacer(1, 40))
    
    signature_style_centered = ParagraphStyle(
    'SignatureCentered',
    parent=styles['Normal'],
    fontSize=10,
    alignment=TA_CENTER,
    leading=12
    )

    # Signature section
    sig_text1 = ""
    sig_text2 = "Name & Signature of the Returning Officer"

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