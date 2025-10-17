import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox, scrolledtext
import requests
import urllib.parse

# GraphHopper API setup
ROUTE_URL = "https://graphhopper.com/api/1/route?"
KEY = "6922dfda-cbee-43b4-b131-44cf1ce77158"

# =========================
# API FUNCTIONS
# =========================
def geocoding(location, key):
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
    except Exception as e:
        messagebox.showerror("Error", f"Geocoding failed: {e}")
        return None


def calculate_route():
    loc1 = entry_loc1.get()
    loc2 = entry_loc2.get()
    vehicle = vehicle_var.get()

    if not loc1 or not loc2:
        messagebox.showwarning("Missing Input", "Please enter both locations.")
        return

    directions_box.delete(1.0, tk.END)
    directions_box.insert(tk.END, "Fetching route...\n")

    orig = geocoding(loc1, KEY)
    dest = geocoding(loc2, KEY)
    if not orig or not dest:
        messagebox.showerror("Error", "Failed to geocode one or both locations.")
        directions_box.insert(tk.END, "❌ Geocoding failed.\n")
        return

    op = f"&point={orig[0]}%2C{orig[1]}"
    dp = f"&point={dest[0]}%2C{dest[1]}"
    route_url = ROUTE_URL + urllib.parse.urlencode({"key": KEY, "vehicle": vehicle}) + op + dp

    try:
        response = requests.get(route_url)
        data = response.json()
        if response.status_code == 200:
            dist_km = data["paths"][0]["distance"] / 1000
            dist_mi = dist_km / 1.61
            time_ms = data["paths"][0]["time"]
            hrs = int(time_ms / 1000 / 60 / 60)
            mins = int(time_ms / 1000 / 60 % 60)
            secs = int(time_ms / 1000 % 60)

            summary = (
                f"From: {orig[2]}\nTo: {dest[2]}\n\n"
                f"Mode: {vehicle.capitalize()}\n"
                f"Distance: {dist_km:.1f} km / {dist_mi:.1f} miles\n"
                f"Duration: {hrs:02d}:{mins:02d}:{secs:02d}"
            )
            messagebox.showinfo("Route Info", summary)

            directions_box.delete(1.0, tk.END)
            directions_box.insert(tk.END, f"{summary}\n\nTurn-by-turn directions:\n")
            directions_box.insert(tk.END, "=====================================\n")

            for each in data["paths"][0]["instructions"]:
                step = each["text"]
                step_dist_km = each["distance"] / 1000
                step_dist_mi = step_dist_km / 1.61
                directions_box.insert(
                    tk.END, f"- {step} ({step_dist_km:.2f} km / {step_dist_mi:.2f} mi)\n"
                )

        else:
            msg = data.get("message", "Unknown error")
            directions_box.insert(tk.END, f"❌ Routing failed: {msg}\n")
            messagebox.showerror("Error", f"Routing failed: {msg}")

    except Exception as e:
        directions_box.insert(tk.END, f"❌ Request failed: {e}\n")
        messagebox.showerror("Error", f"Routing request failed:\n{e}")

# =========================
# GUI SETUP
# =========================
root = tk.Tk()
root.title("MapQuest")
root.geometry("480x550")
root.configure(bg="#b3a9a9")

bg_image = Image.open(r"hoenn2.jpg")
bg_photo = ImageTk.PhotoImage(bg_image)

bg_label = tk.Label(root, image=bg_photo)
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

title = tk.Label(root, text="MapQuest", font=("Helvetica", 22, "bold"), bg="#b3a9a9")
title.pack(pady=10)

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

# Calculate button
calc_btn = tk.Button(root, text="Calculate!", font=("Arial", 12, "bold"), bg="white", command=calculate_route)
calc_btn.pack(pady=10)

# Directions display
directions_box = scrolledtext.ScrolledText(root, width=55, height=15, wrap=tk.WORD, font=("Consolas", 10))
directions_box.pack(padx=10, pady=10)
directions_box.insert(tk.END, "Enter locations and click 'Calculate!' to view directions here.\n")

root.mainloop()
