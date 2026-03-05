from flask import Flask, render_template, request, send_file
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
from io import BytesIO
import re

app = Flask(__name__)

FEED_URL = "PASTE_FEED_URL_HERE"


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

    page = requests.get(vehicle["link"]).text
    match = re.search(r'https://[^"]+\.(jpg|jpeg|png)', page)

    image_url = match.group(0) if match else None
    img_path = None

    if image_url:
        img_data = requests.get(image_url).content
        img = Image.open(BytesIO(img_data))
        img_path = "vehicle.jpg"
        img.save(img_path)

    pdf_file = f"{stock}.pdf"

    c = canvas.Canvas(pdf_file, pagesize=letter)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 750, title)

    c.setFont("Helvetica", 12)
    c.drawString(50, 730, f"Stock: {stock}")
    c.drawString(50, 710, f"VIN: {vin}")
    c.drawString(50, 690, f"Window Sticker: {sticker_url}")

    c.drawString(50, 660, "Manager Notes:")

    text = c.beginText(50, 640)
    text.textLines(notes)
    c.drawText(text)

    if img_path:
        c.drawImage(img_path, 50, 380, width=450, height=250)

    c.showPage()
    c.save()

    return send_file(pdf_file, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
