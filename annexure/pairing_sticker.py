from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak
from reportlab.platypus.flowables import KeepTogether
from pydantic import BaseModel
from typing import List
import uuid

class EVMData(BaseModel):
    evm_no: str
    cu_no: str
    dmm_no: str
    bu_nos: List[str]

def pairing_sticker(data_list: List[EVMData]):

    filename = f"pairing_sticker_{uuid.uuid4().hex[:8]}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4, 
                           topMargin=0.3*inch, bottomMargin=0.3*inch,
                           leftMargin=0.3*inch, rightMargin=0.3*inch)
    
    story = []
    
    # Calculate tables per page: 3 columns x 4 rows = 12 tables per page
    tables_per_page = 12
    
    # Process data in chunks for each page
    for page_chunk in [data_list[i:i+tables_per_page] for i in range(0, len(data_list), tables_per_page)]:
        # Create 4 rows with 3 tables each
        page_rows = []
        
        for row in range(4):
            row_tables = []
            for col in range(3):
                table_index = row * 3 + col
                if table_index < len(page_chunk):
                    table = create_single_table(page_chunk[table_index])
                    row_tables.append(table)
                else:
                    # Add empty space if no more data
                    row_tables.append("")
            
            # Create a table row with 3 tables
            if any(table != "" for table in row_tables):
                row_table = Table([row_tables], 
                                colWidths=[2.5*inch, 2.5*inch, 2.5*inch])
                row_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ]))
                page_rows.append(row_table)
        
        # Add rows to story with minimal spacing
        for i, row in enumerate(page_rows):
            story.append(row)
            if i < len(page_rows) - 1:  # Don't add spacer after last row
                story.append(Spacer(1, 0.1*inch))
        
        # Add page break if more data exists
        if len(data_list) > len(page_chunk) + (len([data_list[i:i+tables_per_page] for i in range(0, len(data_list), tables_per_page)]) - 1) * tables_per_page:
            from reportlab.platypus import PageBreak
            story.append(PageBreak())
    
    doc.build(story)
    print(f"PDF created: {filename}")

def create_single_table(data: EVMData):
    """Create a single EVM table"""
    
    # Ensure we have exactly 4 BU numbers
    bu_nos = data.bu_nos + [""] * (4 - len(data.bu_nos))
    bu_nos = bu_nos[:4]  # Take only first 4
    
    # Table data
    table_data = [
        ["EVM No.", f": {data.evm_no}"],
        ["CU No.", f": {data.cu_no}"],
        ["DMM No.", f": {data.dmm_no}"],
        ["BU No. (1)", f": {bu_nos[0]}"],
        ["BU No. (2)", f": {bu_nos[1]}"],
        ["BU No. (3)", f": {bu_nos[2]}"],
        ["BU No. (4)", f": {bu_nos[3]}"],
    ]
    
    # Create table with smaller dimensions to fit more per page
    table = Table(table_data, colWidths=[1*inch, 1.4*inch])
    
    # Apply styling
    table.setStyle(TableStyle([
        # Background color - pale yellow
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(1, 1, 0.9)),  # Pale yellow
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        
        # Reduced padding to fit more
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        
        # Smaller font to fit more content
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        
        # Alignment
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # First column left aligned
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Second column left aligned
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    return table