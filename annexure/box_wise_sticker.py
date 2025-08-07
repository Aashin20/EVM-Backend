from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from datetime import datetime
from typing import List

def Box_wise_sticker(boxes_data: List, first_component_type:str,filename="Box_wise_sticker.pdf"):
    print(first_component_type)
    if first_component_type == "CU":


        # Create document with landscape orientation
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4), 
                            leftMargin=0.75*inch, rightMargin=0.75*inch, 
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=14,
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
            fontSize=14,
            textColor=colors.gray,
            spaceAfter=6
        )
        header_value_style = ParagraphStyle(
            'HeaderValue',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=16,
            leading=18,
            spaceBefore=6
        )
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER
        )
        
        # Content elements
        elements = []
        
        # Current date
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        # Process each box
        for box_index, box_data in enumerate(boxes_data):
            # Add page break for subsequent boxes
            if box_index > 0:
                elements.append(PageBreak())
            
            # Logo
            try:
                logo = Image("annexure/logo.png", width=1*inch, height=1*inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
            except:
                elements.append(Paragraph("LOGO", title_style))
            
            elements.append(Spacer(1, 12))
            
            # Main Heading
            heading = Paragraph("List of components in corresponding box", title_style)
            elements.append(heading)
            
            elements.append(Spacer(1, 15))
            
            # Helper function to format date
            def format_flc_date(date_str):
                if date_str is None:
                    return "Not Available"
                try:
                    # Parse ISO format and extract date
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return dt.strftime("%d-%m-%Y")
                except:
                    return "Invalid Date"
            
            # Get FLC date from first component (assuming all components in box have same FLC date)
            flc_date = box_data.components[0].flc_date if box_data.components else "Not Available"
            
            # Simplified header info - Box No. and FLC Date
            header_info = [
                [Paragraph("Box No.", header_label_style), Paragraph("FLC Date", header_label_style)],
                [Paragraph(f"<b>{str(box_data.box_no)}</b>", header_value_style), Paragraph(f"<b>{flc_date}</b>", header_value_style)]
            ]
            
            header_table = Table(header_info, colWidths=[200, 200])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 1), (-1, 1), 6),
            ]))
            elements.append(header_table)
            
            elements.append(Spacer(1, 30))
            
            # Split components into two groups (5 each)
            components = box_data.components
            mid_point = len(components) // 2
            left_components = components[:mid_point]
            right_components = components[mid_point:]
            
            # Component table headers
            headers = ["SI No.", "Serial No.", "Status"]
            index_headers = ["1", "2", "3"]
            
            # Create left table data
            left_data = [headers, index_headers]
            for i, comp in enumerate(left_components):
                left_data.append([
                    str(i+1), 
                    comp.serial_no,
                    comp.status
                ])
            
            # Create right table data
            right_data = [headers, index_headers]
            for i, comp in enumerate(right_components):
                right_data.append([
                    str(i+1+len(left_components)), 
                    comp.serial_no,
                    comp.status
                ])
            
            # Add Total Count row only to right table
            right_data.append(["Total Count", str(len(components)), ""])
            
            # Set column widths for each table
            col_widths = [80, 150, 120]
            
            # Create left table
            left_table = Table(left_data, colWidths=col_widths)
            left_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Center headers
                ('ALIGN', (0, 1), (-1, 1), 'CENTER'),  # Center index row
                ('ALIGN', (0, 2), (0, -1), 'CENTER'),  # Center SI No. column
                ('ALIGN', (1, 2), (-1, -1), 'CENTER'),  # Center data cells
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background
                ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),  # Index row background
            ]))
            
            # Create right table
            right_table = Table(right_data, colWidths=col_widths)
            right_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Center headers
                ('ALIGN', (0, 1), (-1, 1), 'CENTER'),  # Center index row
                ('ALIGN', (0, 2), (0, -2), 'CENTER'),  # Center SI No. column (except total row)
                ('ALIGN', (1, 2), (-1, -2), 'CENTER'),  # Center data cells (except total row)
                ('ALIGN', (0, -1), (0, -1), 'LEFT'),   # Left-align "Total Count"
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background
                ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),  # Index row background
            ]))
            
            # Create a container table to place both tables side by side
            container_data = [[left_table, right_table]]
            container_table = Table(container_data, colWidths=[370, 370])
            container_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            
            elements.append(container_table)
        
        # Build document
        doc.build(elements)
        return filename
    
    else:
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
            fontSize=14,
            textColor=colors.gray,
            spaceAfter=6
        )
        header_value_style = ParagraphStyle(
            'HeaderValue',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=16,
            leading=18,
            spaceBefore=6
        )
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER
        )
        
        # Content elements
        elements = []
        
        # Current date
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        # Process each box
        for box_index, box_data in enumerate(boxes_data):
            # Add page break for subsequent boxes
            if box_index > 0:
                elements.append(PageBreak())
            
            # Logo
            try:
                logo = Image("annexure/logo.png", width=1*inch, height=1*inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
            except:
                elements.append(Paragraph("LOGO", title_style))
            
            elements.append(Spacer(1, 12))
            
            # Main Heading
            heading = Paragraph("List of components in corresponding box", title_style)
            elements.append(heading)
            
            elements.append(Spacer(1, 15))
            
            # Helper function to format date
            def format_flc_date(date_str):
                if date_str is None:
                    return "Not Available"
                try:
                    # Parse ISO format and extract date
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return dt.strftime("%d-%m-%Y")
                except:
                    return "Invalid Date"
            
            # Get FLC date from first component (assuming all components in box have same FLC date)
            flc_date = box_data.components[0].flc_date if box_data.components else "Not Available"


            
            # Simplified header info - Box No. and FLC Date
            header_info = [
                [Paragraph("Box No.", header_label_style), Paragraph("FLC Date", header_label_style)],
                [Paragraph(f"<b>{str(box_data.box_no)}</b>", header_value_style), Paragraph(f"<b>{flc_date}</b>", header_value_style)]
            ]
            
            header_table = Table(header_info, colWidths=[160, 160])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
                ('TOPPADDING', (0, 1), (-1, 1), 0),
            ]))
            elements.append(header_table)
            
            elements.append(Spacer(1, 30))
            
            # Component table headers
            headers = ["SI No.", "Serial No.", "Status"]
            
            # Column index headers
            index_headers = ["1", "2", "3"]
            
            # Component table data
            comp_data = [headers, index_headers]
            
            # Add component rows
            components = box_data.components
            for i, comp in enumerate(components):
                comp_data.append([
                    str(i+1), 
                    comp.serial_no,
                    comp.status
                ])

            
            # Add Total Count row
            comp_data.append(["Total Count", str(len(components)), ""])
            
            # Set column widths
            col_widths = [80, 150, 150]
            
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
        
        # Build document
        doc.build(elements)
        return filename