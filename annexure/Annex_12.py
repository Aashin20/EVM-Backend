from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class CUDetail(BaseModel):
    comp_no: str
    comp_type: str  
    comp_box_no: Optional[str] = None
    comp_warehouse: Optional[str] = None
    

def BO_DEO_Return(details: List[CUDetail], order_no: str, alloted_from: str, alloted_to: str, filename="Annexure_12.pdf"):
  
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4), 
                          leftMargin=0.5*inch, rightMargin=0.5*inch, 
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
    title = Paragraph("Annexure - XII", title_style)
    elements.append(title)
    
    # Reference
    reference = Paragraph("(See Para 4.1 (c) of Chapter 4)", subtitle_style)
    elements.append(reference)
    
    # Main Heading
    heading = Paragraph("Register for return of EVM from Block Panchayat Secretary/ERO of Municipality/Corporation to District Election Officer", title_style)
    elements.append(heading)
    
    elements.append(Spacer(1, 15))
    
    # Current date
    current_date = datetime.now().strftime("%d-%m-%Y")
    
    # Horizontal header info
    header_info = [
         [Paragraph("Allotment Order No.", header_label_style),
         Paragraph("Returned From", header_label_style),
         Paragraph("Returned to", header_label_style),
         Paragraph("Date of Return", header_label_style)
         ],
        [Paragraph(order_no, header_value_style),
         Paragraph(alloted_from, header_value_style),
         Paragraph(alloted_to, header_value_style),
         Paragraph(current_date, header_value_style)
         ]
    ]
    
    header_table = Table(header_info, colWidths=[150, 150, 150, 150])
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
        "CU Box No.",
        "CU Warehouse",
        "DMM No. (If Any)",
        "BU No", 
        "BU Box No.",
        "BU Warehouse"
    ]
    
    # Column index headers
    index_headers = ["1", "2", "3", "4", "5", "6", "7", "8"]
    
    # Component table data
    comp_data = [headers, index_headers]
    
    # Separate components by type
    cu_components = [comp for comp in details if comp.comp_type.upper() == 'CU']
    bu_components = [comp for comp in details if comp.comp_type.upper() == 'BU']
    dmm_components = [comp for comp in details if comp.comp_type.upper() == 'DMM']
    
    # Find the maximum number of rows needed
    max_rows = max(len(cu_components), len(bu_components), len(dmm_components))
    
    # Create rows with components packed efficiently
    for i in range(max_rows):
        row = [str(i+1), "", "", "", "", "", "", ""]
        
        # Add CU component if available
        if i < len(cu_components):
            cu_comp = cu_components[i]
            row[1] = cu_comp.comp_no  # CU No.
            row[2] = cu_comp.comp_box_no or ""  # CU Box No.
            row[3] = cu_comp.comp_warehouse or ""  # CU Warehouse
        
        # Add DMM component if available
        if i < len(dmm_components):
            dmm_comp = dmm_components[i]
            row[4] = dmm_comp.comp_no  # DMM No.
        
        # Add BU component if available
        if i < len(bu_components):
            bu_comp = bu_components[i]
            row[5] = bu_comp.comp_no  # BU No
            row[6] = bu_comp.comp_box_no or ""  # BU Box No.
            row[7] = bu_comp.comp_warehouse or ""  # BU Warehouse
        
        comp_data.append(row)
    
    # Add Total Count row
    total_row = ["Total Count", str(len(cu_components)), "", "", str(len(dmm_components)), str(len(bu_components)), "", ""]
    comp_data.append(total_row)
    
    # Set column widths for 8 columns (landscape allows more space)
    col_widths = [60, 80, 100, 110, 110, 80, 100, 110]
    
    comp_table = Table(comp_data, colWidths=col_widths)
    comp_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Center headers
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),  # Center index row
        ('ALIGN', (0, 2), (0, -2), 'CENTER'),  # Center SI No. column
        ('ALIGN', (1, 2), (-1, -2), 'CENTER'),  # Center data cells
        ('ALIGN', (0, -1), (0, -1), 'LEFT'),   # Left-align "Total Count"
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),  # Index row background
    ]))
    elements.append(comp_table)
    
    # Add signature section only at the end
    elements.append(Spacer(1, 40))
    
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

    sig_table = Table(sig_data, colWidths=[250, 200, 250])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(sig_table)
            
    # Build document
    doc.build(elements)
    return filename