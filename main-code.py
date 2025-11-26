import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk
import requests
import urllib.parse
import csv
from datetime import datetime
import webbrowser
import os

# Optional third-party niceties (tabulate for nice tables, colorama for console colors).
# If these aren't installed, the script will continue to run without them.
try:
    from tabulate import tabulate
    HAVE_TABULATE = True
except Exception:
    HAVE_TABULATE = False

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    HAVE_COLORAMA = True
except Exception:
    HAVE_COLORAMA = False

# ---------- Config ----------
ROUTE_URL = "https://graphhopper.com/api/1/route?"
KEY = "6922dfda-cbee-43b4-b131-44cf1ce77158"
HISTORY_FILE = "route_history.csv"
DEFAULT_WINDOW_SIZE = (480, 620)

# Ensure history file exists with header
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "timestamp", "origin", "destination", "vehicle",
            "distance_km", "duration_hms", "fuel_eff_l", "fuel_price_per_l", "fuel_needed_l", "fuel_cost"
        ])

# ---------- State ----------
last_route_data = None  # stores dict of latest route result (meters/ms/instructions etc.)
unit_mode = "km"        # "km" or "mi"

# ---------- Utility functions ----------
def safe_print_console(msg, color=None):
    """Console print with optional colorama coloring."""
    if HAVE_COLORAMA and color:
        print(getattr(Fore, color.upper(), "") + msg + Style.RESET_ALL)
    else:
        print(msg)

def geocoding(location, key):
    """Use GraphHopper geocoding API to get lat/lng and label. Returns (lat, lng, label) or None."""
    if not location or not location.strip():
        return None
    geocode_url = "https://graphhopper.com/api/1/geocode?"
    url = geocode_url + urllib.parse.urlencode({"q": location, "limit": "1", "key": key})
    try:
        r = requests.get(url, timeout=12)
        data = r.json()
        if r.status_code == 200 and data.get("hits"):
            hit = data["hits"][0]
            lat, lng = hit["point"]["lat"], hit["point"]["lng"]
            name = hit.get("name", location)
            country = hit.get("country", "")
            state = hit.get("state", "")
            label = ", ".join(filter(None, [name, state, country]))
            return (lat, lng, label)
    except Exception as e:
        safe_print_console(f"Geocoding error: {e}", color="RED" if HAVE_COLORAMA else None)
    return None

def save_history(row):
    """Append a history row (list) to CSV."""
    try:
        with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(row)
        safe_print_console("Saved route to history.", color="GREEN" if HAVE_COLORAMA else None)
    except Exception as e:
        safe_print_console(f"Failed to save history: {e}", color="RED" if HAVE_COLORAMA else None)

def load_history():
    """Return list of rows (excluding header)."""
    rows = []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            r = csv.reader(f)
            header = next(r, None)
            for row in r:
                rows.append(row)
    except Exception as e:
        safe_print_console(f"Failed to read history: {e}", color="RED" if HAVE_COLORAMA else None)
    return rows

def format_duration(ms):
    s = int(ms / 1000)
    hrs = s // 3600
    mins = (s % 3600) // 60
    secs = s % 60
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"

# ---------- UI helper functions ----------
def tag_insert(text_widget, text, tag=None):
    """Insert text into widget and optionally apply a tag (for color/style)."""
    if tag:
        text_widget.insert(tk.END, text, tag)
    else:
        text_widget.insert(tk.END, text)

def open_maps():
    """Open Google Maps directions in user's web browser using the last route lat/lng."""
    if not last_route_data:
        tag_insert(directions_box, "\n⚠ No route available. Calculate first to open maps.\n", "error")
        return
    orig = last_route_data["orig"]
    dest = last_route_data["dest"]
    vehicle = last_route_data["vehicle"]
    # Use lat,lng for accuracy
    travelmode = {"car": "driving", "bike": "bicycling", "foot": "walking"}.get(vehicle, "driving")
    url = f"https://www.google.com/maps/dir/{orig[0]},{orig[1]}/{dest[0]},{dest[1]}/?travelmode={travelmode}"
    webbrowser.open(url)

# ---------- Core route/calc/diWAsplay ----------
def calculate_route():
    """Fetch route from GraphHopper and populate last_route_data, then show it."""
    global last_route_data, unit_mode
    unit_mode = "km"  # reset to kilometers on new calculation
    directions_box.delete(1.0, tk.END)

    loc1 = entry_loc1.get().strip()
    loc2 = entry_loc2.get().strip()
    vehicle = vehicle_var.get()

    # Fuel inputs - accept blanks or invalid floats gracefully
    try:
        fuel_eff = float(entry_fuel_eff.get()) if entry_fuel_eff.get().strip() else None
    except Exception:
        fuel_eff = None
    try:
        fuel_price = float(entry_fuel_price.get()) if entry_fuel_price.get().strip() else None
    except Exception:
        fuel_price = None

    if not loc1 or not loc2:
        tag_insert(directions_box, "⚠ Please enter both Location 1 and Location 2.\n", "warning")
        return

    tag_insert(directions_box, f"Calculating route from '{loc1}' to '{loc2}' by {vehicle}...\n\n", "header")
    root.update_idletasks()

    orig = geocoding(loc1, KEY)
    dest = geocoding(loc2, KEY)
    if not orig or not dest:
        tag_insert(directions_box, "❌ Error: Failed to geocode one or both locations.\n", "error")
        return

    # Build and request route
    op = f"&point={orig[0]}%2C{orig[1]}"
    dp = f"&point={dest[0]}%2C{dest[1]}"
    route_url = ROUTE_URL + urllib.parse.urlencode({"key": KEY, "vehicle": vehicle}) + op + dp

    try:
        r = requests.get(route_url, timeout=15)
        data = r.json()
        if r.status_code == 200 and data.get("paths"):
            path = data["paths"][0]
            last_route_data = {
                "orig": orig,
                "dest": dest,
                "vehicle": vehicle,
                "distance_m": path["distance"],   # meters
                "time_ms": path["time"],          # milliseconds
                "instructions": path["instructions"]
            }
            # Save to history with fuel calcs below
            distance_km = last_route_data["distance_m"] / 1000.0
            duration_hms = format_duration(last_route_data["time_ms"])
            fuel_needed = (distance_km / fuel_eff) if (fuel_eff and fuel_eff > 0) else None
            fuel_cost = (fuel_needed * fuel_price) if (fuel_needed is not None and fuel_price is not None) else None

            # Persist history row (timestamp, origin label, dest label, vehicle, distance_km, duration, fuel_eff, fuel_price, fuel_needed, fuel_cost)
            ts = datetime.now().isoformat(sep=" ", timespec="seconds")
            row = [
                ts,
                orig[2],
                dest[2],
                vehicle,
                f"{distance_km:.3f}",
                duration_hms,
                f"{fuel_eff:.3f}" if fuel_eff else "",
                f"{fuel_price:.3f}" if fuel_price else "",
                f"{fuel_needed:.3f}" if fuel_needed is not None else "",
                f"{fuel_cost:.2f}" if fuel_cost is not None else ""
            ]
            save_history(row)

            show_route()  # render into the text box
        else:
            msg = data.get("message", "Unknown routing error")
            tag_insert(directions_box, f"❌ Routing failed: {msg}\n", "error")
    except Exception as e:
        tag_insert(directions_box, f"❌ Request failed: {e}\n", "error")

def show_route():
    """Read last_route_data and display summary + turn-by-turn in directions_box respecting unit_mode."""
    directions_box.delete(1.0, tk.END)
    if not last_route_data:
        tag_insert(directions_box, "No route data available. Please calculate first.\n", "warning")
        return

    orig = last_route_data["orig"]
    dest = last_route_data["dest"]
    vehicle = last_route_data["vehicle"]
    dist_m = last_route_data["distance_m"]
    time_ms = last_route_data["time_ms"]
    instructions = last_route_data["instructions"]

    dist_km = dist_m / 1000.0
    dist_mi = dist_km / 1.61
    duration = format_duration(time_ms)

    # Fuel inputs for display
    try:
        fuel_eff = float(entry_fuel_eff.get()) if entry_fuel_eff.get().strip() else None
    except Exception:
        fuel_eff = None
    try:
        fuel_price = float(entry_fuel_price.get()) if entry_fuel_price.get().strip() else None
    except Exception:
        fuel_price = None

    fuel_needed = (dist_km / fuel_eff) if (fuel_eff and fuel_eff > 0) else None
    fuel_cost = (fuel_needed * fuel_price) if (fuel_needed is not None and fuel_price is not None) else None

    # Build summary table (use tabulate if available)
    if unit_mode == "km":
        main_distance_str = f"{dist_km:.2f} km"
    else:
        main_distance_str = f"{dist_mi:.2f} mi"

    summary_rows = [
        ["From", orig[2]],
        ["To", dest[2]],
        ["Mode", vehicle.capitalize()],
        ["Distance", main_distance_str],
        ["Duration", duration],
    ]
    if fuel_eff:
        summary_rows.append(["Fuel eff.", f"{fuel_eff:.2f} km/L"])
    if fuel_needed is not None:
        summary_rows.append(["Fuel needed", f"{fuel_needed:.2f} L"])
    if fuel_price is not None:
        summary_rows.append(["Fuel price per L", f"{fuel_price:.2f}"])
    if fuel_cost is not None:
        summary_rows.append(["Estimated fuel cost", f"{fuel_cost:.2f}"])

    if HAVE_TABULATE:
        summary_text = tabulate(summary_rows, tablefmt="plain")
        tag_insert(directions_box, summary_text + "\n\n", "summary")
    else:
        # simple fallback
        for k, v in summary_rows:
            tag_insert(directions_box, f"{k:15}: {v}\n", "summary")
        tag_insert(directions_box, "\n")

    tag_insert(directions_box, "="*56 + "\n", "divider")
    tag_insert(directions_box, "Turn-by-turn directions:\n\n", "header")

    for each in instructions:
        step_text = each.get("text", "")
        step_dist_km = each.get("distance", 0) / 1000.0
        step_dist_mi = step_dist_km / 1.61
        if unit_mode == "km":
            unit_text = f"{step_dist_km:.2f} km"
        else:
            unit_text = f"{step_dist_mi:.2f} mi"
        tag_insert(directions_box, f"• {step_text} ({unit_text})\n")

    tag_insert(directions_box, "\n" + "="*56 + "\n", "divider")
    tag_insert(directions_box, "✓ Route complete.\n", "ok")

def toggle_units():
    """Toggle between km and mi and re-render."""
    global unit_mode
    if not last_route_data:
        tag_insert(directions_box, "\n⚠ Please calculate a route first.\n", "warning")
        return
    unit_mode = "mi" if unit_mode == "km" else "km"
    # update convert button text to show what it'll switch to next
    convert_btn.configure(text=("Show km" if unit_mode == "mi" else "Show miles"))
    show_route()

def show_history():
    """Load history CSV and display as a table in the box."""
    rows = load_history()
    directions_box.delete(1.0, tk.END)
    if not rows:
        tag_insert(directions_box, "No history yet.\n", "warning")
        return

    # Reverse chronological
    rows_rev = list(reversed(rows))
    headers = ["timestamp", "origin", "destination", "vehicle", "distance_km", "duration", "fuel_eff_l", "fuel_price", "fuel_needed_l", "fuel_cost"]
    if HAVE_TABULATE:
        text = tabulate(rows_rev, headers=headers, tablefmt="grid")
        tag_insert(directions_box, "Route history (most recent first):\n\n", "header")
        tag_insert(directions_box, text + "\n", "summary")
    else:
        tag_insert(directions_box, "Route history (most recent first):\n\n", "header")
        for r in rows_rev:
            tag_insert(directions_box, ", ".join(r) + "\n", "summary")

# ---------- GUI setup ----------
root = tk.Tk()
root.title("MapQuest")
w, h = DEFAULT_WINDOW_SIZE
root.geometry(f"{w}x{h}")
root.configure(bg="#b3a9a9")

# Background image (optional)
try:
    bg_image = Image.open("hoenn2.jpg").resize((w, h))
    bg_photo = ImageTk.PhotoImage(bg_image)
    bg_label = tk.Label(root, image=bg_photo)
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
except Exception:
    # no image — OK
    pass

# Title
title = tk.Label(root, text="MapQuest", font=("Helvetica", 22, "bold"), bg="#b3a9a9")
title.pack(pady=6)

# Input frame
frame = tk.Frame(root, bg="#b3a9a9")
frame.pack(pady=6)

tk.Label(frame, text="Location 1", font=("Arial", 11), bg="#b3a9a9").grid(row=0, column=0, padx=8, pady=6, sticky="w")
entry_loc1 = tk.Entry(frame, width=30)
entry_loc1.grid(row=0, column=1, padx=6, pady=6)

tk.Label(frame, text="Location 2", font=("Arial", 11), bg="#b3a9a9").grid(row=1, column=0, padx=8, pady=6, sticky="w")
entry_loc2 = tk.Entry(frame, width=30)
entry_loc2.grid(row=1, column=1, padx=6, pady=6)

# Fuel inputs row
fuel_frame = tk.Frame(root, bg="#b3a9a9")
fuel_frame.pack(pady=4)

tk.Label(fuel_frame, text="Fuel eff. (km/L)", font=("Arial", 10), bg="#b3a9a9").grid(row=0, column=0, padx=6)
entry_fuel_eff = tk.Entry(fuel_frame, width=8)
entry_fuel_eff.grid(row=0, column=1, padx=6)
tk.Label(fuel_frame, text="Fuel price per L", font=("Arial", 10), bg="#b3a9a9").grid(row=0, column=2, padx=6)
entry_fuel_price = tk.Entry(fuel_frame, width=8)
entry_fuel_price.grid(row=0, column=3, padx=6)

# Vehicle selection
vehicle_var = tk.StringVar(value="car")
vehicle_frame = tk.Frame(root, bg="#b3a9a9")
vehicle_frame.pack(pady=8)

for mode in ["car", "bike", "foot"]:
    tk.Radiobutton(
        vehicle_frame,
        text=mode.capitalize(),
        variable=vehicle_var,
        value=mode,
        indicatoron=False,
        width=8,
        pady=5,
        font=("Arial", 10, "bold"),
        bg="white"
    ).pack(side="left", padx=8)

# Buttons frame
btn_frame = tk.Frame(root, bg="#b3a9a9")
btn_frame.pack(pady=8)

calc_btn = tk.Button(btn_frame, text="Calculate!", font=("Arial", 11, "bold"), bg="white", command=calculate_route)
calc_btn.pack(side="left", padx=8)

convert_btn = tk.Button(btn_frame, text="Show miles", font=("Arial", 11, "bold"), bg="white", command=toggle_units)
convert_btn.pack(side="left", padx=8)

maps_btn = tk.Button(btn_frame, text="Open in Maps", font=("Arial", 11, "bold"), bg="white", command=open_maps)
maps_btn.pack(side="left", padx=8)

history_btn = tk.Button(btn_frame, text="Show History", font=("Arial", 11, "bold"), bg="white", command=show_history)
history_btn.pack(side="left", padx=8)

clear_btn = tk.Button(btn_frame, text="Clear", font=("Arial", 11, "bold"), bg="white", command=lambda: directions_box.delete(1.0, tk.END))
clear_btn.pack(side="left", padx=8)

# Directions / output box
directions_box = scrolledtext.ScrolledText(root, width=58, height=20, wrap=tk.WORD, font=("Consolas", 10))
directions_box.pack(padx=10, pady=8)

# Configure some tags to simulate colored/formatted output in the UI
directions_box.tag_config("header", foreground="#003366", font=("Consolas", 11, "bold"))
directions_box.tag_config("summary", foreground="#002244", font=("Consolas", 10))
directions_box.tag_config("divider", foreground="#666666")
directions_box.tag_config("error", foreground="#aa0000")
directions_box.tag_config("ok", foreground="#0a6a0a")
directions_box.tag_config("warning", foreground="#aa6600")

directions_box.insert(tk.END, "Enter two locations and click 'Calculate!' to view your route here.\n")

# Start the GUI
root.mainloop()