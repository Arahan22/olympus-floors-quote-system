from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import math
import csv
import os
from datetime import datetime

app = FastAPI()

ADMIN_PIN = '2204'


QUOTES_FILE = "quotes.csv"
PRODUCTS_FILE = "products.csv"

def save_product(name, price, box):
    file_exists = os.path.isfile(PRODUCTS_FILE)
    with open(PRODUCTS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["name", "price", "box"])
        writer.writerow([name, price, box])

def load_products():
    if not os.path.isfile(PRODUCTS_FILE):
        return []
    with open(PRODUCTS_FILE, "r") as f:
        return list(csv.DictReader(f))

def save_quote(data):
    file_exists = os.path.isfile(QUOTES_FILE)
    with open(QUOTES_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

@app.get("/", response_class=HTMLResponse)
def home():
    products = load_products()

    options = ""
    for p in products:
        options += f"<option value='{p['name']}|{p['price']}|{p['box']}'>{p['name']}</option>"

    return f"""
    <html>
    <head>
        <title>Olympus Floors</title>
    </head>
    <body>

    <h1>Olympus Floors Quote System</h1>

    <form action="/calc" method="post">

    <h3>Customer</h3>
    <input name="customer_name" placeholder="Name"><br>
    <input name="phone" placeholder="Phone"><br><br>

    <h3>Quote Type</h3>
    <select name="mode">
        <option value="manual">Manual</option>
        <option value="saved">Saved Product</option>
    </select><br><br>

    <h3>Saved Product</h3>
    <select id="saved_product" name="saved_product" onchange="fillProduct()">
        <option value="">-- Select --</option>
        {options}
    </select><br><br>

    <h3>Product Info</h3>
    <input id="product" name="product" placeholder="Product"><br>
    <input id="price" name="price" step="0.01" placeholder="Price"><br>
    <input id="box" name="box" step="0.01" placeholder="Sqft per box"><br><br>

    <h3>Project</h3>
    <input name="sqft" step="0.01" placeholder="Sqft"><br>
    <input name="waste" value="10"><br><br>

    <h3>Tax</h3>
    <select name="tax_mode">
        <option value="yes">Yes</option>
        <option value="no">No</option>
    </select><br>
    <input name="tax_rate" value="7"><br><br>

    <button>Generate</button>

    </form>

    <script>
    function fillProduct() {{
        let val = document.getElementById("saved_product").value;
        if(val) {{
            let parts = val.split("|");
            document.getElementById("product").value = parts[0];
            document.getElementById("price").value = parts[1];
            document.getElementById("box").value = parts[2];
        }}
    }}
    </script>

    <br>
    <a href="/admin">Add Product</a><br><a href="/products">View / Delete Products</a><br>
    <a href="/quotes">View Quotes</a>

    </body>
    </html>
    """

@app.post("/calc", response_class=HTMLResponse)
def calc(customer_name: str = Form(...), phone: str = Form(...),
         mode: str = Form(...), saved_product: str = Form(""),
         product: str = Form(""), price: float = Form(0),
         box: float = Form(0), sqft: float = Form(...),
         waste: float = Form(10), tax_mode: str = Form("yes"),
         tax_rate: float = Form(7)):

    if mode == "saved" and saved_product:
        name, price, box = saved_product.split("|")
        price = float(price)
        box = float(box)
        product = name

    sqft_waste = sqft * (1 + waste/100)
    boxes = math.ceil(sqft_waste / box)
    total = sqft * price

    if tax_mode == "yes":
        total += total * (tax_rate/100)

    save_quote({
        "customer": customer_name,
        "product": product,
        "boxes": boxes,
        "total": round(total, 2)
    })

    return f"<h1>Total: ${round(total,2)}</h1><a href='/'>Back</a>"

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return '''
    <h1>Admin Login</h1>
    <form method="post" action="/admin_login">
        <input name="pin" placeholder="Enter PIN" type="password">
        <button>Enter</button>
    </form>
    <a href="/">Back</a>
    '''
def admin():
    return """
    <h1>Add Product</h1>
    <form method="post">
    <input name="name" placeholder="Name"><br>
    <input name="price"><br>
    <input name="box"><br>
    <button>Add</button>
    </form>
    <a href="/">Back</a>
    """

@app.post("/add_product", response_class=HTMLResponse)
def add(name: str = Form(...), price: float = Form(...), box: float = Form(...)):
    save_product(name, price, box)
    return "<h2>Added</h2><a href='/'>Back</a>"


@app.get("/products", response_class=HTMLResponse)
def products():
    products = load_products()

    rows = ""
    for p in products:
        rows += f"""
        <tr>
            <td>{p['name']}</td>
            <td>${p['price']}</td>
            <td>{p['box']}</td>
            <td>
                <form action="/delete_product" method="post">
                    <input type="hidden" name="name" value="{p['name']}">
                    <button>Delete</button>
                </form>
            </td>
        </tr>
        """

    return f"""
    <h1>Saved Products</h1>
    <table border="1">
        <tr><th>Name</th><th>Price</th><th>Sqft/Box</th><th>Action</th></tr>
        {rows}
    </table>
    <br>
    <a href="/admin">Add Product</a><br><a href="/products">View / Delete Products</a><br>
    <a href="/">Back</a>
    """

@app.post("/delete_product", response_class=HTMLResponse)
def delete_product(name: str = Form(...)):
    products = load_products()
    products = [p for p in products if p["name"] != name]

    with open(PRODUCTS_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "price", "box"])
        for p in products:
            writer.writerow([p["name"], p["price"], p["box"]])

    return "<h2>Product Deleted</h2><a href='/products'>Back to Products</a>"

@app.get("/quotes", response_class=HTMLResponse)
def quotes():
    if not os.path.isfile(QUOTES_FILE):
        return "<h2>No quotes yet</h2>"

    rows = ""
    with open(QUOTES_FILE) as f:
        for r in csv.DictReader(f):
            rows += f"<tr><td>{r['customer']}</td><td>{r['product']}</td><td>${r['total']}</td></tr>"

    return f"<table border=1><tr><th>Name</th><th>Product</th><th>Total</th></tr>{rows}</table><br><a href='/'>Back</a>"
