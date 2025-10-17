import tkinter as tk
from PIL import Image, ImageTk
from tkinter import scrolledtext
import requests
import urllib.parse

# GraphHopper API setup
ROUTE_URL = "https://graphhopper.com/api/1/route?"
KEY = "6922dfda-cbee-43b4-b131-44cf1ce77158"

# =========================
# GLOBAL STATE
# =========================
last_route_data = None  # To store the most recent route info
unit_mode = "km"  # Default unit mode


# =========================
# API FUNCTIONS
# =========================
def geocoding(location, key):
    """Geocode a location string using GraphHopper."""
    if not location.strip():
        return None
    geocode_url = "https://graphhopper.com/api/1/geocode?"
    url = geocode_url + urllib.parse.urlencode({"q": location, "limit": "1", "key": key})
    try:
        reply = requests.get(url)
        data = reply.json()
        if reply.status_code == 200 and data["hits"]:
            hit = data["hits"][0]
            lat, lng = hit["point"]["lat"], hit["point"]["lng"]
            name = hit.get("name", location)
            country = hit.get("country", "")
            state = hit.get("state", "")
            label = ", ".join(filter(None, [name, state, country]))
            return (lat, lng, label)
        else:
            return None
    except Exception:
        return None


def calculate_route():
    """Calculate the route and display results in directions box."""
    global last_route_data, unit_mode
    unit_mode = "km"  # Reset to default each new calculation
    loc1 = entry_loc1.get()
    loc2 = entry_loc2.get()
    vehicle = vehicle_var.get()

    directions_box.delete(1.0, tk.END)

    if not loc1 or not loc2:
        directions_box.insert(tk.END, "⚠ Please enter both locations.\n")
        return

    directions_box.insert(tk.END, f"Calculating route from '{loc1}' to '{loc2}' by {vehicle}...\n\n")

    orig = geocoding(loc1, KEY)
    dest = geocoding(loc2, KEY)
    if not orig or not dest:
        directions_box.insert(tk.END, "❌ Error: Failed to geocode one or both locations.\n")
        return

    op = f"&point={orig[0]}%2C{orig[1]}"
    dp = f"&point={dest[0]}%2C{dest[1]}"
    route_url = ROUTE_URL + urllib.parse.urlencode({"key": KEY, "vehicle": vehicle}) + op + dp

    try:
        response = requests.get(route_url)
        data = response.json()

        if response.status_code == 200:
            path = data["paths"][0]
            last_route_data = {
                "orig": orig,
                "dest": dest,
                "vehicle": vehicle,
                "distance": path["distance"],  # meters
                "time": path["time"],  # milliseconds
                "instructions": path["instructions"],
            }
            show_route()
        else:
            msg = data.get("message", "Unknown error")
            directions_box.insert(tk.END, f"❌ Routing failed: {msg}\n")

    except Exception as e:
        directions_box.insert(tk.END, f"❌ Request failed: {e}\n")


def show_route():
    """Display route info based on current unit mode."""
    directions_box.delete(1.0, tk.END)

    if not last_route_data:
        directions_box.insert(tk.END, "No route data available. Please calculate first.\n")
        return

    orig = last_route_data["orig"]
    dest = last_route_data["dest"]
    vehicle = last_route_data["vehicle"]
    dist_m = last_route_data["distance"]
    time_ms = last_route_data["time"]
    instructions = last_route_data["instructions"]

    dist_km = dist_m / 1000
    dist_mi = dist_km / 1.61
    hrs = int(time_ms / 1000 / 60 / 60)
    mins = int(time_ms / 1000 / 60 % 60)
    secs = int(time_ms / 1000 % 60)

    if unit_mode == "km":
        summary = (
            f"From: {orig[2]}\n"
            f"To: {dest[2]}\n"
            f"Mode: {vehicle.capitalize()}\n"
            f"Distance: {dist_km:.1f} km\n"
            f"Duration: {hrs:02d}:{mins:02d}:{secs:02d}\n"
            f"{'='*45}\n\nTurn-by-turn directions:\n\n"
        )
    else:
        summary = (
            f"From: {orig[2]}\n"
            f"To: {dest[2]}\n"
            f"Mode: {vehicle.capitalize()}\n"
            f"Distance: {dist_mi:.1f} miles\n"
            f"Duration: {hrs:02d}:{mins:02d}:{secs:02d}\n"
            f"{'='*45}\n\nTurn-by-turn directions:\n\n"
        )

    directions_box.insert(tk.END, summary)

    for each in instructions:
        step = each["text"]
        step_dist_km = each["distance"] / 1000
        step_dist_mi = step_dist_km / 1.61
        if unit_mode == "km":
            directions_box.insert(tk.END, f"• {step} ({step_dist_km:.2f} km)\n")
        else:
            directions_box.insert(tk.END, f"• {step} ({step_dist_mi:.2f} mi)\n")

    directions_box.insert(tk.END, f"\n{'='*45}\n✓ Route complete.\n")


def toggle_units():
    """Switch between kilometers and miles view."""
    global unit_mode
    if not last_route_data:
        directions_box.insert(tk.END, "\n⚠ Please calculate a route first.\n")
        return

    unit_mode = "mi" if unit_mode == "km" else "km"
    show_route()


# =========================
# GUI SETUP
# =========================
root = tk.Tk()
root.title("MapQuest")
root.geometry("480x580")
root.configure(bg="#b3a9a9")

# Background image
try:
    bg_image = Image.open(r"hoenn2.jpg").resize((480, 580))
    bg_photo = ImageTk.PhotoImage(bg_image)
    bg_label = tk.Label(root, image=bg_photo)
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
except Exception:
    pass  # If no image, continue normally

# Title
title = tk.Label(root, text="MapQuest", font=("Helvetica", 22, "bold"), bg="#b3a9a9")
title.pack(pady=10)

# Input frame
frame = tk.Frame(root, bg="#b3a9a9")
frame.pack(pady=10)

tk.Label(frame, text="Location 1", font=("Arial", 12), bg="#b3a9a9").grid(row=0, column=0, padx=10, pady=5)
entry_loc1 = tk.Entry(frame, width=30)
entry_loc1.grid(row=0, column=1)

tk.Label(frame, text="Location 2", font=("Arial", 12), bg="#b3a9a9").grid(row=1, column=0, padx=10, pady=5)
entry_loc2 = tk.Entry(frame, width=30)
entry_loc2.grid(row=1, column=1)

# Vehicle selection
vehicle_var = tk.StringVar(value="car")
vehicle_frame = tk.Frame(root, bg="#b3a9a9")
vehicle_frame.pack(pady=10)

for mode in ["car", "bike", "foot"]:
    tk.Radiobutton(
        vehicle_frame,
        text=mode.capitalize(),
        variable=vehicle_var,
        value=mode,
        indicatoron=False,
        width=8,
        pady=5,
        font=("Arial", 11, "bold"),
        bg="white"
    ).pack(side="left", padx=10)

# Buttons frame
btn_frame = tk.Frame(root, bg="#b3a9a9")
btn_frame.pack(pady=10)

calc_btn = tk.Button(btn_frame, text="Calculate!", font=("Arial", 12, "bold"), bg="white", command=calculate_route)
calc_btn.pack(side="left", padx=10)

convert_btn = tk.Button(btn_frame, text="Convert!", font=("Arial", 12, "bold"), bg="white", command=toggle_units)
convert_btn.pack(side="left", padx=10)

# Directions box
directions_box = scrolledtext.ScrolledText(root, width=55, height=16, wrap=tk.WORD, font=("Consolas", 10))
directions_box.pack(padx=10, pady=10)
directions_box.insert(tk.END, "Enter two locations and click 'Calculate!' to view your route here.\n")

root.mainloop()