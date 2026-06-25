"""Generate a simple synthetic invoice PDF for testing the pipeline.

Field labels mirror what Azure Document Intelligence's prebuilt-invoice model
looks for (vendor, customer, invoice id, dates, line items, totals).
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def build(path: str = "samples/sample_invoice.pdf") -> str:
    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter
    x = inch

    c.setFont("Helvetica-Bold", 20)
    c.drawString(x, h - inch, "INVOICE")

    c.setFont("Helvetica", 11)
    lines_top = [
        "Contoso Supplies Ltd.",
        "123 Market Street",
        "Seattle, WA 98101",
        "",
        "Invoice Number: INV-2026-00042",
        "Invoice Date: 2026-06-01",
        "Due Date: 2026-07-01",
        "Purchase Order: PO-7781",
        "",
        "Bill To:",
        "Fabrikam Inc.",
        "456 Industrial Ave",
        "Portland, OR 97201",
    ]
    y = h - 1.6 * inch
    for line in lines_top:
        c.drawString(x, y, line)
        y -= 0.25 * inch

    # Line items table
    y -= 0.2 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Description")
    c.drawString(x + 3.2 * inch, y, "Qty")
    c.drawString(x + 4.0 * inch, y, "Unit Price")
    c.drawString(x + 5.2 * inch, y, "Amount")
    y -= 0.05 * inch
    c.line(x, y, w - inch, y)
    y -= 0.25 * inch

    c.setFont("Helvetica", 11)
    items = [
        ("Widget Assembly Kit", "10", "$45.00", "$450.00"),
        ("Mounting Brackets", "25", "$3.20", "$80.00"),
        ("Shipping & Handling", "1", "$25.00", "$25.00"),
    ]
    for desc, qty, price, amt in items:
        c.drawString(x, y, desc)
        c.drawString(x + 3.2 * inch, y, qty)
        c.drawString(x + 4.0 * inch, y, price)
        c.drawString(x + 5.2 * inch, y, amt)
        y -= 0.25 * inch

    # Totals
    y -= 0.3 * inch
    c.setFont("Helvetica", 11)
    c.drawString(x + 4.0 * inch, y, "Subtotal:")
    c.drawString(x + 5.2 * inch, y, "$555.00")
    y -= 0.25 * inch
    c.drawString(x + 4.0 * inch, y, "Tax (8%):")
    c.drawString(x + 5.2 * inch, y, "$44.40")
    y -= 0.25 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x + 4.0 * inch, y, "Total Due:")
    c.drawString(x + 5.2 * inch, y, "$599.40")

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    print("Wrote", build())
