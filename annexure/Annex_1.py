from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch
from typing import List,Dict
from datetime import datetime



def CU_1(components: List, component_type: str, warehouse_names: Dict[int, str],alloted_to:str, order_no:str,filename="Annexure_1.pdf"):
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
    title = Paragraph("Annexure - I", title_style)
    elements.append(title)
    
    # Reference
    reference = Paragraph("(See Para 2.4 (f) & 2.5 (c) of Chapter 2)", subtitle_style)
    elements.append(reference)
    
    # Main Heading
    heading = Paragraph("Receipt of allotted EVM components to District Election Officers", title_style)
    elements.append(heading)
    
    elements.append(Spacer(1, 15))
    
    # Current date
    current_date = datetime.now().strftime("%d-%m-%Y")
    
    # Horizontal header info
    header_info = [
        [Paragraph("SEC's Allotment Order No.", header_label_style), 
         Paragraph("Date", header_label_style), 
         Paragraph("Allotted From", header_label_style),
         Paragraph("Allotted To", header_label_style)],
        [Paragraph(order_no, header_value_style), 
         Paragraph(current_date, header_value_style), 
         Paragraph("SEC", header_value_style),
         Paragraph(alloted_to, header_value_style)]
    ]
    
    header_table = Table(header_info, colWidths=[120, 120, 120, 120])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
    ]))
    elements.append(header_table)
    
    elements.append(Spacer(1, 30))
    
    # Component type for the headers
    component_label = component_type if component_type in ["CU", "BU"] else "Component"
    
    # Column headers
    headers = [
        "SI No.", 
        f"{component_label} No.", 
        f"Month & Year of\nManufacture of {component_label}", 
        f"{component_label} Box No", 
        "Warehouse"
    ]
    
    # Column index headers
    index_headers = ["1", "2", "3", "4", "5"]
    
    # Component table data
    comp_data = [headers, index_headers]
    
    # Add component rows
    for i, comp in enumerate(components):
        warehouse_name = warehouse_names.get(comp.current_warehouse_id, "Unknown")
        warehouse_name = "TVM1"
        dom_formatted = comp.dom.strftime("%m/%Y") if hasattr(comp.dom, 'strftime') else comp.dom
        
        comp_data.append([
            str(i+1), 
            comp.serial_number,
            dom_formatted,
            str(comp.box_no),
            warehouse_name
        ])
    
    # Add Total Count row directly after the data (no empty rows)
    comp_data.append(["Total Count", str(len(components)), "", "", ""])
    
    # Set column widths to give more space to warehouse column
    col_widths = [60, 90, 110, 80, 170]  # Significantly increased warehouse column width
    
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

def DMM_1(components: List, component_type: str,alloted_to:str,order_no:str, filename="Annexure_1.pdf"):
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
    title = Paragraph("Annexure - I", title_style)
    elements.append(title)
    
    # Reference
    reference = Paragraph("(See Para 2.4 (f) & 2.5 (c) of Chapter 2)", subtitle_style)
    elements.append(reference)
    
    # Main Heading
    heading = Paragraph("Receipt of allotted EVM components to District Election Officers", title_style)
    elements.append(heading)
    
    elements.append(Spacer(1, 15))
    
    # Current date
    current_date = datetime.now().strftime("%d-%m-%Y")
    
    # Horizontal header info - FIXED: Added 4th column width
    header_info = [
        [Paragraph("SEC's Allotment Order No.", header_label_style), 
         Paragraph("Date", header_label_style), 
         Paragraph("Allotted From", header_label_style),
         Paragraph("Allotted To", header_label_style)],
        [Paragraph(order_no, header_value_style), 
         Paragraph(current_date, header_value_style), 
         Paragraph("SEC", header_value_style),
         Paragraph(alloted_to, header_value_style)]
    ]
    
    header_table = Table(header_info, colWidths=[120, 120, 120, 120])  # FIXED: Added 4th width
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
    ]))
    elements.append(header_table)
    
    elements.append(Spacer(1, 30))
    
    # Component type for the headers
    component_label = component_type 
    
    headers = [
            "SI No.", 
            f"{component_label} No.", 
            f"Month & Year of\nManufacture of {component_label}", 
        ]
        
        # Column index headers
    index_headers = ["1", "2", "3"]
        
        # Component table data
    comp_data = [headers, index_headers]
        
        # Add component rows
    for i, comp in enumerate(components):
            dom_formatted = comp.dom.strftime("%m/%Y") if hasattr(comp.dom, 'strftime') else comp.dom
            
            comp_data.append([
                str(i+1), 
                comp.serial_number,
                dom_formatted,
            ])
        
        # Add Total Count row - FIXED: Only 3 columns
    comp_data.append(["Total Count", str(len(components)), ""])  # FIXED: Only 3 values
        
        # Set column widths to give more space
    col_widths = [60, 120, 150]  # Adjusted widths for better spacing
        
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
