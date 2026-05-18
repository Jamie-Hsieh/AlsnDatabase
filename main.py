import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

DATA_DB = "data.db"
CONFIG_FILE = "config.json"
TEMPLATE_DIR = "templates"

# -----------------------------
# CONFIG & DB INITIALIZATION
# -----------------------------

def ensure_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "fields": [
                {"name": "field_a", "label": "Field A", "type": "text", "default": True},
                {"name": "field_b", "label": "Field B", "type": "text", "default": True},
                {
                    "name": "status",
                    "label": "Status",
                    "type": "select",
                    "options": ["Open", "Closed", "Pending"],
                    "default": True
                },
                {"name": "date_field", "label": "Date", "type": "date", "default": True},
                {"name": "timestamp", "label": "Timestamp", "type": "timestamp", "default": True}
            ]
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

CONFIG = ensure_config()


def get_db_connection():
    conn = sqlite3.connect(DATA_DB)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Create table if it doesn't exist
    field_defs = ", ".join([f'{f["name"]} TEXT' for f in CONFIG["fields"]])
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {field_defs}
        )
    """)

    # Get existing columns
    cur.execute("PRAGMA table_info(entries)")
    existing_cols = {row["name"] for row in cur.fetchall()}

    # Add missing columns
    for field in CONFIG["fields"]:
        name = field["name"]
        if name not in existing_cols:
            cur.execute(f"ALTER TABLE entries ADD COLUMN {name} TEXT")

    conn.commit()
    conn.close()


# -----------------------------
# AUTO-CREATE TEMPLATES
# -----------------------------

if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)

# ---------- INDEX TEMPLATE ----------
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
        {% for field in fields %}
            {% if field.type != 'timestamp' %}
                <label>{{ field.label }}:</label><br>

                {% if field.type == "text" %}
                    <input type="text" name="{{ field.name }}">

                {% elif field.type == "date" %}
                    <input type="date" name="{{ field.name }}">

                {% elif field.type == "select" %}
                    <select name="{{ field.name }}">
                        {% for option in field.options %}
                            <option value="{{ option }}">{{ option }}</option>
                        {% endfor %}
                    </select>

                {% endif %}

                <br><br>
            {% endif %}
        {% endfor %}

        <button type="submit">Confirm</button>
    </form>

    <br><br>

    <a href="/report"><button type="button">Generate Report</button></a>
</body>
</html>
        """)

# ---------- REPORT TEMPLATE ----------
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

        <label>Filter by date:</label><br><br>

        <select name="filter_type">
            <option value="">No Filter</option>
            <option value="before" {% if filter_type == 'before' %}selected{% endif %}>Before</option>
            <option value="after" {% if filter_type == 'after' %}selected{% endif %}>After</option>
        </select>

        <input type="date" name="filter_date" value="{{ filter_date or '' }}">

        <br><br>

        <label>Show fields:</label><br>

        {% for field in fields %}
            {% set param_name = 'show_' + field.name %}
            <input type="checkbox"
                   name="{{ param_name }}"
                   value="on"
                   {% if checkbox_states[field.name] %}checked{% endif %}>
            {{ field.label }}<br>
        {% endfor %}

        <br>
        <button type="submit">Apply</button>
    </form>

    <hr>

    {% for e in entries %}
        <p>
            <strong>Entry:</strong><br>
            {% for field in fields %}
                {% if checkbox_states[field.name] %}
                    {{ field.label }}:
                    {% if field.type == "date" %}
                        {{ e[field.name][:10] }}
                    {% else %}
                        {{ e[field.name] }}
                    {% endif %}
                    <br>
                {% endif %}
            {% endfor %}
        </p>
        <hr>
    {% endfor %}
</body>
</html>
        """)

ensure_db()

# -----------------------------
# ROUTES
# -----------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        values = {}

        for field in CONFIG["fields"]:
            name = field["name"]
            ftype = field.get("type", "text")

            if ftype == "timestamp":
                values[name] = datetime.now().isoformat()

            elif ftype == "select":
                val = request.form.get(name, "")
                if val not in field.get("options", []):
                    val = ""
                values[name] = val

            else:
                values[name] = request.form.get(name, "")

        conn = get_db_connection()
        cur = conn.cursor()

        columns = ", ".join(values.keys())
        placeholders = ", ".join(["?"] * len(values))
        sql = f"INSERT INTO entries ({columns}) VALUES ({placeholders})"

        cur.execute(sql, list(values.values()))

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("index.html", fields=CONFIG["fields"])


@app.route("/report")
def report():
    filter_type = request.args.get("filter_type")
    filter_date = request.args.get("filter_date")

    
    sql = "SELECT * FROM entries"
    params = []
    conditions = []


    has_timestamp = any(f["name"] == "timestamp" for f in CONFIG["fields"])

    if has_timestamp and filter_type and filter_date:
        if filter_type == "before":
            sql += " WHERE timestamp < ?"
            params.append(filter_date)
        elif filter_type == "after":
            sql += " WHERE timestamp > ?"
            params.append(filter_date)

    search_query = request.args.get("search")

    if search_query: #search bar
        search_conditions = []
        for field in CONFIG["fields"]:
            name = field["name"]
            search_conditions.append(f"{name} LIKE ?")
            params.append(f"%{search_query}%")

        conditions.append("(" + " OR ".join(search_conditions) + ")")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(sql, params)
    rows = cur.fetchall()

    conn.close()

    entries = []
    for row in rows:
        entry = {}
        for field in CONFIG["fields"]:
            entry[field["name"]] = row[field["name"]]
        entries.append(entry)

    
    checkbox_states = {}

    # Check if ANY checkbox parameters were submitted
    has_checkbox_params = any(
        key.startswith("show_") for key in request.args
    )

    for field in CONFIG["fields"]:
        param_name = f"show_{field['name']}"

        if not has_checkbox_params:
            # First load → use config defaults (yours are True)
            checkbox_states[field["name"]] = field.get("default", True)
        else:
            # After form submission:
            # checkbox is ON only if it appears in the request
            checkbox_states[field["name"]] = (param_name in request.args)



    return render_template(
        "report.html",
        fields=CONFIG["fields"],
        entries=entries,
        checkbox_states=checkbox_states,
        filter_type=filter_type,
        filter_date=filter_date
    )


# -----------------------------
# RUN APP
# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)