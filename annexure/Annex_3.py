from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (Table, TableStyle, Paragraph,
                                SimpleDocTemplate, Spacer, Image)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
from typing import List
from reportlab.lib.units import inch
import uuid

def FLC_Certificate_BU(components: List[dict]):
    filename = f"Annexure_3_{uuid.uuid4().hex[:8]}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4, 
                            leftMargin=0.5*inch, rightMargin=0.5*inch, 
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=12,
        spaceAfter=6
    )
    
    elements = []
    
    try:
        logo = Image("annexure/logo.png", width=1*inch, height=1*inch)
        logo.hAlign = 'CENTER'
        elements.append(logo)
    except:
        elements.append(Paragraph("LOGO", title_style))
    
    elements.extend([
        Spacer(1, 12),
        Paragraph("Annexure III", title_style),
        Paragraph("First Level Check", title_style),
        Paragraph("CERTIFICATE", title_style),
        Spacer(1, 15)
    ])
    
  
    sorted_components = sorted(components, key=lambda x: (not x["passed"], x.get("serial_number", "")))
    
    headers = [
        "SI\nNo", "BU No", "FLC Date", "FLC\nStatus\n(Passed/\nFailed)",
        "Signature of\nECIL Engineer", "Signature of\nrepresentative of\npolitical parties",
        "Signature of\nDistrict Election\nOfficer or\nofficer\nauthorised by\nhim"
    ]
    
    index_headers = ["1", "2", "3", "4", "5", "6", "7"]
    
 
    comp_data = [headers, index_headers]
    
    
    for i, comp in enumerate(sorted_components):
        receipt_date = comp.get("date_of_receipt")
        flc_date = receipt_date.strftime("%d-%m-%Y") if receipt_date else datetime.now().strftime("%d-%m-%Y")
        
        comp_data.append([
            str(i+1), 
            comp["serial_number"],
            flc_date,
            "Passed" if comp["passed"] else "Failed",
            "", "", ""
        ])
    
    col_widths = [35, 70, 70, 70, 90, 90, 90]
    
    comp_table = Table(comp_data, colWidths=col_widths)
    comp_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('BACKGROUND', (0, 2), (-1, -1), colors.white),
        ('LINEBELOW', (4, 2), (6, -1), 0, colors.white),
        ('LINEABOVE', (4, 3), (6, -1), 0, colors.white),
        ('BACKGROUND', (4, 2), (6, -1), colors.white),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(comp_table)
    
    doc.build(elements)
    return filename


def FLC_Certificate_CU(components: List[dict]):
    filename = f"Annexure_3_{uuid.uuid4().hex[:8]}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4), 
                            leftMargin=0.5*inch, rightMargin=0.5*inch, 
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=13,
        spaceAfter=6
    )
    
    elements = []
    
    try:
        logo = Image("annexure/logo.png", width=1.1*inch, height=1.1*inch)
        logo.hAlign = 'CENTER'
        elements.append(logo)
    except:
        elements.append(Paragraph("LOGO", title_style))
    
    elements.extend([
        Spacer(1, 12),
        Paragraph("Annexure III", title_style),
        Paragraph("First Level Check", title_style),
        Paragraph("CERTIFICATE", title_style),
        Spacer(1, 15)
    ])
    

    sorted_components = sorted(components, key=lambda x: (not x["passed"], x.get("cu_number", "")))
    
    headers = [
        "SI\nNo", "CU NO", "DMM NO", "DMM Seal\nNo", "CU Pink\nPaper Seal\nNo",
        "FLC Date", "FLC\nStatus\n(Passed/\nFailed)", "Signature of\nECIL Engineer",
        "Signature of\nrepresentative of\npolitical parties",
        "Signature of\nDistrict Election\nOfficer or\nofficer\nauthorised by\nhim"
    ]
    
    index_headers = ["1", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
    
  
    comp_data = [headers, index_headers]
    

    for i, comp in enumerate(sorted_components):
        receipt_date = comp.get("date_of_receipt")
        flc_date = receipt_date.strftime("%d-%m-%Y") if receipt_date else datetime.now().strftime("%d-%m-%Y")
        
        comp_data.append([
            str(i+1), 
            comp["cu_number"],    
            comp["dmm_number"],   
            comp["dmm_seal_no"],  
            comp["cu_pink_seal"], 
            flc_date,
            "Passed" if comp["passed"] else "Failed",
            "", "", ""
        ])
    
    col_widths = [35, 80, 80, 80, 80, 80, 80, 90, 90, 90]
    
    comp_table = Table(comp_data, colWidths=col_widths)
    comp_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('BACKGROUND', (0, 2), (-1, -1), colors.white),
        ('LINEBELOW', (7, 2), (9, -1), 0, colors.white),
        ('LINEABOVE', (7, 3), (9, -1), 0, colors.white),
        ('BACKGROUND', (7, 2), (9, -1), colors.white),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(comp_table)
    
    doc.build(elements)
    return filename