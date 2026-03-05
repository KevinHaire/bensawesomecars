from flask import Flask, render_template, request, send_file
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
import os
import re

app = Flask(__name__)

FEED_URL = "https://www.bourgeoismotors.com/inventory/feed"


def get_vehicle(stock):
    r = requests.get(FEED_URL)
    data = r.json()

    for vehicle in data:
        if vehicle["stockNum"].lower() == stock.lower():
            return vehicle

    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():

    stock = request.form["stock"]
    notes = request.form["notes"]

    vehicle = get_vehicle(stock)

    if not vehicle:
        return "Vehicle not found"

    title = f'{vehicle["year"]} {vehicle["make"]} {vehicle["model"]}'
    vin = vehicle["vin"]

    sticker_url = f"https://www.windowsticker.forddirect.com/windowsticker.pdf?vin={vin}"

    image_url = vehicle["pictureURL"]
    img_path = None

    # fallback if pictureURL is missing
    if image_url == "N/A":
        try:
            page = requests.get(vehicle["link"]).text
            match = re.search(r'https://[^"]+\.(jpg|jpeg|png)', page)
            image_url = match.group(0) if match else None
        except:
            image_url = None

    # download vehicle image
    if image_url:
        try:
            img_data = requests.get(image_url).content
            img = Image.open(BytesIO(img_data))
            img_path = f"{stock}_vehicle.jpg"
            img.save(img_path)
        except:
            img_path = None

    # download window sticker
    sticker_file = None
    try:
        r = requests.get(sticker_url)
        if r.status_code == 200:
            sticker_file = f"{stock}_sticker.pdf"
            with open(sticker_file, "wb") as f:
                f.write(r.content)
    except:
        sticker_file = None

    pdf_file = f"{stock}.pdf"

    # create first page PDF
    c = canvas.Canvas(pdf_file, pagesize=letter)

    page_width, page_height = letter

    # title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 750, title)

    # vehicle info
    c.setFont("Helvetica", 12)
    c.drawString(50, 725, f"Stock: {stock}")
    c.drawString(50, 705, f"VIN: {vin}")

    # manager notes
    c.drawString(50, 675, "Manager Notes:")

    text = c.beginText(50, 655)
    text.setFont("Helvetica", 11)
    text.textLines(notes)
    c.drawText(text)

    # vehicle image centered at 80% width
    if img_path:
        try:
            img = Image.open(img_path)
            img_w, img_h = img.size

            target_width = page_width * 0.8
            scale = target_width / img_w

            new_width = target_width
            new_height = img_h * scale

            x_position = (page_width - new_width) / 2
            y_position = 300

            c.drawImage(img_path, x_position, y_position, width=new_width, height=new_height)

        except:
            pass

    c.showPage()
    c.save()

    # merge with window sticker
    if sticker_file:

        writer = PdfWriter()

        main_pdf = PdfReader(pdf_file)
        sticker_pdf = PdfReader(sticker_file)

        for page in main_pdf.pages:
            writer.add_page(page)

        for page in sticker_pdf.pages:
            writer.add_page(page)

        merged_file = f"{stock}_complete.pdf"

        with open(merged_file, "wb") as f:
            writer.write(f)

        return send_file(merged_file, as_attachment=True)

    return send_file(pdf_file, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
