from flask import Flask, render_template, request, redirect
import sqlite3
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import io
from datetime import datetime
print("App starting...")
from flask import session
app = Flask(__name__)
app.secret_key = "secret123"

# Initialize Database
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    service TEXT,
    risk_score INTEGER,
    risk_level TEXT,
    date TEXT
)
""")
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")

@app.route("/add_vendor", methods=["POST"])
def add_vendor():
    name = request.form["name"]
    service = request.form["service"]
    mfa = request.form["mfa"]
    encryption = request.form["encryption"]
    breach = request.form["breach"]
    pii = request.form["pii"]
    compliance = request.form["compliance"]

    score = 0

    if mfa == "No": score += 20
    if encryption == "No": score += 25
    if breach == "Yes": score += 30
    if pii == "Yes": score += 20
    if compliance == "ISO": score -= 15

    if score <= 30:
        level = "Low"
    elif score <= 60:
        level = "Medium"
    else:
        level = "High"

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO vendors (name, service, risk_score, risk_level, date) VALUES (?, ?, ?, ?, ?)",
        (name, service, score, level, datetime.now())
    )
    conn.commit()
    conn.close()

    return render_template(
    "result.html",
    name=name,
    score=score,
    level=level
)
@app.route("/vendors")
def vendors():
    if "user" not in session:
        return redirect("/login")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors ORDER BY id DESC")
    data = cursor.fetchall()
    conn.close()

    low = sum(1 for v in data if v[4] == "Low")
    medium = sum(1 for v in data if v[4] == "Medium")
    high = sum(1 for v in data if v[4] == "High")

    names = [v[1] for v in data]
    scores = [v[3] for v in data]

    return render_template(
        "vendors.html",
        vendors=data,
        low=low,
        medium=medium,
        high=high,
        names=names,
        scores=scores
        
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            session["user"] = username
            return redirect("/vendors")
        else:
            return render_template("login.html", error="Invalid Credentials")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            conn.close()
            return render_template("register.html", error="Username already exists")

   
    return render_template("register.html")
@app.route("/download/<name>/<int:score>/<level>")
def download(name, score, level):

    from flask import send_file
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph("Vendor Risk Assessment Report", styles["Title"]))
    elements.append(Spacer(1, 20))

    data = [
        ["Vendor Name", name],
        ["Risk Score", str(score)],
        ["Risk Level", level],
    ]

    table = Table(data)
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="vendor_report.pdf",
        mimetype="application/pdf"
    )
if __name__ == "__main__":
    app.run(debug=True)
    