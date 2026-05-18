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

    field_defs = ", ".join([f'{f["name"]} TEXT' for f in CONFIG["fields"]])
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {field_defs}
        )
    """)

    cur.execute("PRAGMA table_info(entries)")
    existing_cols = {row["name"] for row in cur.fetchall()}

    for field in CONFIG["fields"]:
        name = field["name"]
        if name not in existing_cols:
            cur.execute(f'ALTER TABLE entries ADD COLUMN "{name}" TEXT')

    conn.commit()
    conn.close()


# -----------------------------
# AUTO-CREATE TEMPLATES
# -----------------------------

if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)

report_html = os.path.join(TEMPLATE_DIR, "report.html")
if not os.path.exists(report_html):
    with open(report_html, "w", encoding="utf-8") as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Report</title>
</head>
<body>

<h1>Report</h1>

<div style="display: flex; gap: 40px; align-items: flex-start;">

    <!-- LEFT SIDE -->
    <div style="flex: 2;">

        <form method="GET">

            <label>Search:</label><br>
            <input type="text" name="search" value="{{ request.args.get('search', '') }}">
            <br><br>

            <label>Filter by date:</label><br><br>

            <select name="filter_type">
                <option value="">No Filter</option>
                <option value="before" {% if filter_type == 'before' %}selected{% endif %}>Before</option>
                <option value="after" {% if filter_type == 'after' %}selected{% endif %}>After</option>
            </select>

            <input type="date" name="filter_date" value="{{ filter_date or '' }}">

            <br><br>

            <label>Show & Filter Fields:</label><br>

            {% for field in fields %}
                {% set checkbox_name = 'show_' + field.name %}
                {% set filter_name = 'filter_' + field.name %}

                <input type="checkbox"
                       name="{{ checkbox_name }}"
                       value="on"
                       {% if checkbox_states[field.name] %}checked{% endif %}>

                {{ field.label }}

                {% if field.type == "text" %}
                    <input type="text" name="{{ filter_name }}" value="{{ request.args.get(filter_name, '') }}">

                {% elif field.type == "select" %}
                    <select name="{{ filter_name }}">
                        <option value="">--Any--</option>
                        {% for option in field.options %}
                            <option value="{{ option }}"
                                {% if request.args.get(filter_name) == option %}selected{% endif %}>
                                {{ option }}
                            </option>
                        {% endfor %}
                    </select>

                {% elif field.type == "date" %}
                    <input type="date" name="{{ filter_name }}" value="{{ request.args.get(filter_name, '') }}">
                {% endif %}

                <br><br>
            {% endfor %}

            <button type="submit">Apply</button>

            <br><br>

            <button type="button" onclick="checkAll()">Check All</button>
            <button type="button" onclick="uncheckAll()">Uncheck All</button>
            <button type="button" onclick="resetForm()">Reset Fields</button>

        </form>

        <hr>

        {% for e in entries %}
            <p>
                <strong>Entry:</strong><br>
                {% for field in fields %}
                    {% if checkbox_states[field.name] %}
                        {{ field.label }}: {{ e[field.name] }}<br>
                    {% endif %}
                {% endfor %}
            </p>
            <hr>
        {% endfor %}

    </div>

    <!-- RIGHT SIDE -->
    <div style="flex: 1; border-left: 1px solid #ccc; padding-left: 20px;">

        <h2>Enter New Record</h2>

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

            <button type="submit">Add Entry</button>
        </form>

    </div>

</div>

<script>

function checkAll() {
    document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });
}

function uncheckAll() {
    document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
}

function resetForm() {
    const form = document.querySelector('form');
    form.reset();
    window.location.href = "/report";
}

</script>

</body>
</html>
        """)

ensure_db()

# -----------------------------
# ROUTES
# -----------------------------

@app.route("/")
def home():
    return redirect("/report")


@app.route("/report", methods=["GET", "POST"])
def report():

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

        return redirect("/report")

    filter_type = request.args.get("filter_type")
    filter_date = request.args.get("filter_date")
    search_query = request.args.get("search", "").strip()

    sql = "SELECT * FROM entries"
    params = []
    conditions = []

    has_timestamp = any(f["name"] == "timestamp" for f in CONFIG["fields"])

    if has_timestamp and filter_type and filter_date:
        if filter_type == "before":
            conditions.append("timestamp < ?")
            params.append(filter_date)
        elif filter_type == "after":
            conditions.append("timestamp > ?")
            params.append(filter_date)

    if search_query:
        search_conditions = []
        for field in CONFIG["fields"]:
            if field["type"] == "timestamp":
                continue
            name = field["name"]
            search_conditions.append(f"LOWER({name}) LIKE LOWER(?)")
            params.append(f"%{search_query}%")

        conditions.append("(" + " OR ".join(search_conditions) + ")")

    for field in CONFIG["fields"]:
        name = field["name"]
        ftype = field.get("type", "text")
        filter_val = request.args.get(f"filter_{name}")

        if filter_val:
            if ftype == "text":
                conditions.append(f"LOWER({name}) LIKE LOWER(?)")
                params.append(f"%{filter_val}%")
            elif ftype == "select":
                conditions.append(f"{name} = ?")
                params.append(filter_val)
            elif ftype == "date":
                conditions.append(f"{name} = ?")
                params.append(filter_val)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

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
    form_submitted = len(request.args) > 0

    for field in CONFIG["fields"]:
        param_name = f"show_{field['name']}"

        if not form_submitted:
            checkbox_states[field["name"]] = field.get("default", True)
        else:
            checkbox_states[field["name"]] = (param_name in request.args)

    return render_template(
        "report.html",
        fields=CONFIG["fields"],
        entries=entries,
        checkbox_states=checkbox_states,
        filter_type=filter_type,
        filter_date=filter_date
    )


if __name__ == "__main__":
    app.run(debug=True)