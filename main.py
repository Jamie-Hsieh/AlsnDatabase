import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

DATA_FILE = "data.json"
TEMPLATE_DIR = "templates"

# -----------------------------
# AUTO-CREATE FOLDERS & FILES
# -----------------------------

# Create templates folder
if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)

# Create data.json if missing
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

# Create index.html if missing (DATA ENTRY PAGE)
index_html = os.path.join(TEMPLATE_DIR, "index.html")
if not os.path.exists(index_html):
    with open(index_html, "w") as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Data Entry</title>
</head>
<body>
    <h1>Enter New Record</h1>

    <form method="POST">
        <label>A:</label><br>
        <input type="text" name="A"><br><br>

        <label>B:</label><br>
        <input type="text" name="B"><br><br>

        <label>C:</label><br>
        <input type="text" name="C"><br><br>

        <button type="submit">Confirm</button>
    </form>

    <br><br>

    <a href="/report"><button>Generate Report</button></a>
</body>
</html>
        """)

# Create report.html if missing (REPORT PAGE WITH CHECKBOXES)
report_html = os.path.join(TEMPLATE_DIR, "report.html")
if not os.path.exists(report_html):
    with open(report_html, "w") as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Report</title>
</head>
<body>
    <h1>Report</h1>

    <form method="GET">

        <!-- Date filter -->
        <label>Filter by date:</label><br><br>

        <select name="filter_type">
            <option value="">No Filter</option>
            <option value="before">Before</option>
            <option value="after">After</option>
        </select>

        <input type="date" name="filter_date">

        <br><br>

        <!-- Checkbox toggles -->
        <label>Show fields:</label><br>

        <input type="checkbox" name="show_A" value="on" {% if show_A %}checked{% endif %}> A<br>
        <input type="checkbox" name="show_B" value="on" {% if show_B %}checked{% endif %}> B<br>
        <input type="checkbox" name="show_C" value="on" {% if show_C %}checked{% endif %}> C<br>
        <input type="checkbox" name="show_timestamp" value="on" {% if show_timestamp %}checked{% endif %}> Timestamp<br>

        <br>
        <button type="submit">Apply</button>
    </form>

    <hr>

    {% for e in entries %}
        <p>
            <strong>Entry:</strong><br>

            {% if show_A %}A: {{ e["A"] }}<br>{% endif %}
            {% if show_B %}B: {{ e["B"] }}<br>{% endif %}
            {% if show_C %}C: {{ e["C"] }}<br>{% endif %}
            {% if show_timestamp %}Time: {{ e["timestamp"] }}<br>{% endif %}
        </p>
        <hr>
    {% endfor %}
</body>
</html>
        """)


# -----------------------------
# DATA HELPERS
# -----------------------------

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# -----------------------------
# ROUTES
# -----------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        entry = {
            "A": request.form["A"],
            "B": request.form["B"],
            "C": request.form["C"],
            "timestamp": datetime.now().isoformat()
        }

        data = load_data()
        data.append(entry)
        save_data(data)

        return redirect("/")

    return render_template("index.html")


@app.route("/report")
def report():
    data = load_data()

    # Date filtering
    filter_type = request.args.get("filter_type")
    filter_date = request.args.get("filter_date")

    if filter_type and filter_date:
        try:
            filter_dt = datetime.fromisoformat(filter_date)
            if filter_type == "before":
                data = [d for d in data if datetime.fromisoformat(d["timestamp"]) < filter_dt]
            elif filter_type == "after":
                data = [d for d in data if datetime.fromisoformat(d["timestamp"]) > filter_dt]
        except:
            pass

    # Checkbox toggles
    show_A = request.args.get("show_A", "on") == "on"
    show_B = request.args.get("show_B", "on") == "on"
    show_C = request.args.get("show_C", "on") == "on"
    show_timestamp = request.args.get("show_timestamp", "off") == "on"

    return render_template(
        "report.html",
        entries=data,
        show_A=show_A,
        show_B=show_B,
        show_C=show_C,
        show_timestamp=show_timestamp
    )

# -----------------------------
# RUN APP
# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)
