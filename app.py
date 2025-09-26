from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
import glob
import os
import csv
import json
from datetime import datetime
import subprocess


APP_DIR = os.path.dirname(os.path.abspath(__file__))
PLATFORMS = {
    'blinkit': {
        'pattern': os.path.join(APP_DIR, "blinkit_pepe_*.csv"),
        'display_name': 'Blinkit'
    },
    'instamart': {
        'pattern': os.path.join(APP_DIR, "*instamart*.csv"),
        'display_name': 'Instamart'
    },
    'zepto': {
        'pattern': os.path.join(APP_DIR, "zepto_pepe_*.csv"),
        'display_name': 'Zepto'
    }
}
BENCHMARKS_PATH = os.path.join(APP_DIR, "benchmarks.json")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "pepe-secret")


def find_latest_csv(platform='blinkit'):
    if platform not in PLATFORMS:
        platform = 'blinkit'  # default fallback
    pattern = PLATFORMS[platform]['pattern']
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return files[0] if files else None


def load_products(csv_path):
    products = []
    if not csv_path or not os.path.exists(csv_path):
        return products
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Ensure numeric-like fields remain strings for display; cast later when needed
            products.append({
                "name": row.get("name", ""),
                "current_price": row.get("current_price", ""),
                "original_price": row.get("original_price", ""),
                "discount": row.get("discount", ""),
                "sizes": row.get("sizes", ""),
            })
    return products


def load_benchmarks():
    if not os.path.exists(BENCHMARKS_PATH):
        return {}
    try:
        with open(BENCHMARKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_benchmarks(data):
    with open(BENCHMARKS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change-this-secret")


def is_unlocked() -> bool:
    return bool(session.get("bench_unlocked"))


def build_view_model(platform='blinkit'):
    csv_path = find_latest_csv(platform)
    products = load_products(csv_path)
    benchmarks = load_benchmarks()
    for p in products:
        key = p["name"]
        p["benchmark_price"] = benchmarks.get(key, "")
        # Compute status and diff
        status = ""
        diff = ""
        cur = p.get("current_price")
        bench = p.get("benchmark_price")
        try:
            cur_val = float(cur)
            bench_val = float(bench)
            diff_val = cur_val - bench_val
            status = "above" if diff_val > 0 else ("below" if diff_val < 0 else "equal")
            diff = f"{diff_val:.2f}"
        except Exception:
            pass
        p["status"] = status
        p["diff"] = diff
    updated_at = datetime.fromtimestamp(os.path.getmtime(csv_path)).strftime("%Y-%m-%d %H:%M:%S") if csv_path else ""
    return products, updated_at, os.path.basename(csv_path) if csv_path else None, platform


@app.route("/")
def index():
    platform = request.args.get('platform', 'blinkit')
    products, updated_at, csv_name, platform = build_view_model(platform)
    return render_template("dashboard.html", products=products, updated_at=updated_at, csv_path=csv_name, platform=platform, platforms=PLATFORMS, unlocked=is_unlocked())


@app.route("/unlock", methods=["POST"])
def unlock():
    key = request.form.get("key", "").strip()
    platform = request.form.get("platform", "blinkit")
    next_page = request.form.get("next", "dashboard")
    if key and key == ADMIN_KEY:
        session["bench_unlocked"] = True
    # redirect to desired page keeping platform
    if next_page == "benchmarks":
        return redirect(url_for("benchmarks_page", platform=platform))
    return redirect(url_for("index", platform=platform))


@app.route("/lock")
def lock():
    session.pop("bench_unlocked", None)
    platform = request.args.get('platform', 'blinkit')
    return redirect(url_for("index", platform=platform))


@app.route("/benchmarks", methods=["GET"])
def benchmarks_page():
    if not is_unlocked():
        # send back to dashboard for unlock
        platform = request.args.get('platform', 'blinkit')
        return redirect(url_for("index", platform=platform))
    platform = request.args.get('platform', 'blinkit')
    products, updated_at, csv_name, platform = build_view_model(platform)
    return render_template("benchmarks.html", products=products, updated_at=updated_at, csv_path=csv_name, platform=platform, platforms=PLATFORMS, unlocked=True)


@app.route("/benchmarks/save", methods=["POST"])
def save_benchmarks_route():
    if not is_unlocked():
        platform = request.form.get('platform', 'blinkit')
        return redirect(url_for("index", platform=platform))
    form = request.form
    platform = form.get('platform', 'blinkit')
    benchmarks = load_benchmarks()
    # Expect inputs named as price_name_<index> with a hidden field name_<index>
    for key, value in form.items():
        if key.startswith("price_"):
            name_key = key.replace("price_", "name_")
            product_name = form.get(name_key, "").strip()
            if product_name:
                try:
                    benchmarks[product_name] = float(value)
                except Exception:
                    benchmarks[product_name] = value
    save_benchmarks(benchmarks)
    return redirect(url_for("benchmarks_page", platform=platform))


@app.route("/export")
def export():
    platform = request.args.get('platform', 'blinkit')
    csv_path = find_latest_csv(platform)
    products = load_products(csv_path)
    benchmarks = load_benchmarks()

    export_path = os.path.join(APP_DIR, f"export_with_benchmarks_{platform}.csv")
    with open(export_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "name",
            "current_price",
            "original_price",
            "discount",
            "sizes",
            "benchmark_price",
            "status",
            "diff",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in products:
            name = p["name"]
            cur = p.get("current_price") or ""
            bench = benchmarks.get(name, "")
            status = ""
            diff = ""
            try:
                cur_val = float(cur)
                bench_val = float(bench)
                diff_val = cur_val - bench_val
                status = "above" if diff_val > 0 else ("below" if diff_val < 0 else "equal")
                diff = f"{diff_val:.2f}"
            except Exception:
                pass
            row = dict(p)
            row.update({
                "benchmark_price": bench,
                "status": status,
                "diff": diff,
            })
            writer.writerow(row)

    return send_file(export_path, as_attachment=True)


@app.route("/tasks/run-scrapers", methods=["POST"])
def run_scrapers_task():
    # Require admin key via header or form
    key = request.headers.get("X-Admin-Key") or request.form.get("key") or ""
    if key != ADMIN_KEY:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    python_bin = os.environ.get("PYTHON_BIN") or os.path.join(APP_DIR, 'venv', 'bin', 'python')
    if not os.path.exists(python_bin):
        python_bin = 'python'
    code = subprocess.call([python_bin, os.path.join(APP_DIR, 'run_all_scrapers.py')], cwd=APP_DIR)
    return jsonify({"ok": code == 0, "code": code})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


