from pathlib import Path
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw


def statement_rows():
    rows = [
        ("01/01/2024", "SALARY CREDIT ACME", "", "50000.00", "150000.00"),
        ("03/01/2024", "UPI SWIGGY ORDER", "450.00", "", "149550.00"),
        ("05/01/2024", "AMAZON PURCHASE", "1200.00", "", "148350.00"),
        ("07/01/2024", "ELECTRICITY BILL", "2300.00", "", "146050.00"),
    ]
    return rows


def create_text_pdf(path):
    canvas = Canvas(str(path), pagesize=A4)
    canvas.setFont("Helvetica", 10)
    lines = ["HDFC Bank", "Account Holder: Priya Sharma", "Account Number: 123456789012", "IFSC: HDFC0001234", "Account Type: Savings", "Opening Balance: 100000.00", "Date|Description|Debit|Credit|Balance"]
    lines += ["|".join(row) for row in statement_rows()]
    for line in lines:
        canvas.drawString(45, 800, line) if line == lines[0] else None
    y = 780
    for line in lines:
        canvas.drawString(45, y, line); y -= 18
    canvas.save()


def create_scanned_pdf(path):
    image = Image.new("RGB", (1654, 2339), "white")
    draw = ImageDraw.Draw(image)
    lines = ["SBI", "Account Holder: Rahul Kumar", "Account Number: 9876543210", "IFSC: SBIN0004567", "Date|Description|Debit|Credit|Balance"] + ["|".join(row) for row in statement_rows()]
    for index, line in enumerate(lines):
        draw.text((100, 100 + index * 55), line, fill="black")
    image.save(path, "PDF", resolution=200.0)


if __name__ == "__main__":
    output = Path("data/synthetic"); output.mkdir(parents=True, exist_ok=True)
    create_text_pdf(output / "text_statement.pdf")
    create_scanned_pdf(output / "scanned_statement.pdf")
    print(output)
