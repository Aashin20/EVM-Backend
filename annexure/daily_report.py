from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from typing import List, Dict
import uuid
import os
import logging

def daily_report(district_data: List[Dict], report_date: str, totals: Dict) -> str:
    try:
        # Kerala districts mapping
        kerala_districts_short = [
            "TVM", "KLM", "PTA", "ALP", "KTM", "IDK", "EKM", 
            "TSR", "PKD", "MLP", "KKD", "WYD", "KNR", "KSD"
        ]
        kerala_districts = [
            "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha",
            "Kottayam", "Idukki", "Ernakulam", "Thrissur", "Palakkad",
            "Malappuram", "Kozhikode", "Wayanad", "Kannur", "Kasaragod"
        ]

        # Create unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"FLC_Daily_Report_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
        
        # Ensure the file path is in a writable directory
        pdf_dir = "generated_reports"
        os.makedirs(pdf_dir, exist_ok=True)
        filepath = os.path.join(pdf_dir, filename)
        
        # Create document - landscape orientation
        doc = SimpleDocTemplate(
            filepath, 
            pagesize=landscape(A4),
            leftMargin=0.5*inch, 
            rightMargin=0.5*inch,
            topMargin=0.5*inch, 
            bottomMargin=0.5*inch
        )

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=9,
            spaceAfter=2
        )
        header_label_style = ParagraphStyle(
            'HeaderLabel',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=8,
            textColor=colors.gray
        )
        header_value_style = ParagraphStyle(
            'HeaderValue',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=9,
            leading=10
        )

        # Content elements
        elements = []

        # Add logo if available
        logo_path = "annexure/logo.png"
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=0.6*inch, height=0.6*inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
            except Exception as e:
                logging.warning(f"Could not load logo: {e}")
                elements.append(Paragraph("ELECTION COMMISSION LOGO", title_style))
        else:
            elements.append(Paragraph("ELECTION COMMISSION LOGO", title_style))

        elements.append(Spacer(1, 4))

        # Main heading
        heading = Paragraph("Daily Progress Report of FLC of EVMs", title_style)
        elements.append(heading)
        elements.append(Spacer(1, 6))

        # Date header
        date_header_info = [
            [Paragraph("Date", header_label_style)],
            [Paragraph(report_date, header_value_style)]
        ]

        date_header_table = Table(date_header_info, colWidths=[200])
        date_header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
            ('TOPPADDING', (0, 1), (-1, 1), 0),
        ]))
        elements.append(date_header_table)
        elements.append(Spacer(1, 12))

        # Table headers
        headers = [
            ["District", "No. of EVMs checked till date", "", "", "", "", "", 
             "No. of EVMs checked on the date", "", "", "", "", "", 
             "Total", "", "", "", "", ""],
            ["", "CU", "", "", "BU", "", "", "CU", "", "", "BU", "", "", 
             "CU", "", "", "BU", "", ""],
            ["", "Pass", "Fail", "Total", "Pass", "Fail", "Total", 
             "Pass", "Fail", "Total", "Pass", "Fail", "Total", 
             "Pass", "Fail", "Total", "Pass", "Fail", "Total"]
        ]
        table_data = headers.copy()

        # Create lookup dictionary for efficient data access
        data_dict = {data_row.get('district', ''): data_row for data_row in district_data}

        # Add district rows
        for i, district in enumerate(kerala_districts):
            short_form = kerala_districts_short[i]
            data_row = data_dict.get(district, {})
            
            # Extract values with defaults
            cu_till_pass = data_row.get('cu_till_pass', 0)
            cu_till_fail = data_row.get('cu_till_fail', 0)
            cu_till_total = cu_till_pass + cu_till_fail
            bu_till_pass = data_row.get('bu_till_pass', 0)
            bu_till_fail = data_row.get('bu_till_fail', 0)
            bu_till_total = bu_till_pass + bu_till_fail

            cu_on_pass = data_row.get('cu_on_pass', 0)
            cu_on_fail = data_row.get('cu_on_fail', 0)
            cu_on_total = cu_on_pass + cu_on_fail
            bu_on_pass = data_row.get('bu_on_pass', 0)
            bu_on_fail = data_row.get('bu_on_fail', 0)
            bu_on_total = bu_on_pass + bu_on_fail

            cu_grand_pass = cu_till_pass + cu_on_pass
            cu_grand_fail = cu_till_fail + cu_on_fail
            cu_grand_total = cu_grand_pass + cu_grand_fail
            bu_grand_pass = bu_till_pass + bu_on_pass
            bu_grand_fail = bu_till_fail + bu_on_fail
            bu_grand_total = bu_grand_pass + bu_grand_fail

            row_values = [
                cu_till_pass, cu_till_fail, cu_till_total,
                bu_till_pass, bu_till_fail, bu_till_total,
                cu_on_pass, cu_on_fail, cu_on_total,
                bu_on_pass, bu_on_fail, bu_on_total,
                cu_grand_pass, cu_grand_fail, cu_grand_total,
                bu_grand_pass, bu_grand_fail, bu_grand_total
            ]

            row = [short_form] + [str(value) for value in row_values]
            table_data.append(row)

        # Add totals row using database-fetched totals
        cu_till_pass_total = totals.get('cu_till_pass', 0)
        cu_till_fail_total = totals.get('cu_till_fail', 0)
        cu_till_total_total = cu_till_pass_total + cu_till_fail_total
        bu_till_pass_total = totals.get('bu_till_pass', 0)
        bu_till_fail_total = totals.get('bu_till_fail', 0)
        bu_till_total_total = bu_till_pass_total + bu_till_fail_total

        cu_on_pass_total = totals.get('cu_on_pass', 0)
        cu_on_fail_total = totals.get('cu_on_fail', 0)
        cu_on_total_total = cu_on_pass_total + cu_on_fail_total
        bu_on_pass_total = totals.get('bu_on_pass', 0)
        bu_on_fail_total = totals.get('bu_on_fail', 0)
        bu_on_total_total = bu_on_pass_total + bu_on_fail_total

        cu_grand_pass_total = cu_till_pass_total + cu_on_pass_total
        cu_grand_fail_total = cu_till_fail_total + cu_on_fail_total
        cu_grand_total_total = cu_grand_pass_total + cu_grand_fail_total
        bu_grand_pass_total = bu_till_pass_total + bu_on_pass_total
        bu_grand_fail_total = bu_till_fail_total + bu_on_fail_total
        bu_grand_total_total = bu_grand_pass_total + bu_grand_fail_total

        total_row_values = [
            cu_till_pass_total, cu_till_fail_total, cu_till_total_total,
            bu_till_pass_total, bu_till_fail_total, bu_till_total_total,
            cu_on_pass_total, cu_on_fail_total, cu_on_total_total,
            bu_on_pass_total, bu_on_fail_total, bu_on_total_total,
            cu_grand_pass_total, cu_grand_fail_total, cu_grand_total_total,
            bu_grand_pass_total, bu_grand_fail_total, bu_grand_total_total
        ]

        total_row = ["Total"] + [str(value) for value in total_row_values]
        table_data.append(total_row)

        # Create and style table
        col_widths = [50, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30]
        main_table = Table(table_data, colWidths=col_widths)
        
        total_row_index = len(table_data) - 1
        
        table_style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 0), (-1, 2), colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 3), (-1, -2), [colors.white, colors.Color(0.95, 0.95, 0.95)]),

            # Header spans
            ('SPAN', (1, 0), (6, 0)),   # "No. of EVMs checked till date"
            ('SPAN', (7, 0), (12, 0)),  # "No. of EVMs checked on the date"
            ('SPAN', (13, 0), (18, 0)), # "Total"

            ('SPAN', (1, 1), (3, 1)),   # CU till
            ('SPAN', (4, 1), (6, 1)),   # BU till
            ('SPAN', (7, 1), (9, 1)),   # CU on
            ('SPAN', (10, 1), (12, 1)), # BU on
            ('SPAN', (13, 1), (15, 1)), # CU total
            ('SPAN', (16, 1), (18, 1)), # BU total

            ('SPAN', (0, 0), (0, 2)),   # District column

            # Total row styling
            ('BACKGROUND', (0, total_row_index), (-1, total_row_index), colors.lightblue),
            ('FONTSIZE', (0, total_row_index), (-1, total_row_index), 8),
            ('FONTNAME', (0, total_row_index), (-1, total_row_index), 'Helvetica-Bold'),
        ]
        
        main_table.setStyle(TableStyle(table_style))
        elements.append(main_table)

        # Build PDF
        doc.build(elements)
        
        # Verify file was created
        if not os.path.exists(filepath):
            raise Exception("PDF file was not created successfully")
            
        logging.info(f"Successfully generated FLC report: {filepath}")
        return filepath
        
    except Exception as e:
        logging.error(f"Error generating PDF report: {str(e)}")
        raise Exception(f"Failed to generate PDF report: {str(e)}")