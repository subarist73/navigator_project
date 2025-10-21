import tkinter as tk
from tkinter import ttk, messagebox
import requests
import folium
import webview
import os

# ===== Поиск адреса через Nominatim =====
def search_addresses(query):
    if not query or len(query) < 3:
        return []
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "addressdetails": 1, "limit": 5}
    headers = {"User-Agent": "NavigatorApp/1.0 (support@example.com)"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        return [(d["display_name"], float(d["lat"]), float(d["lon"])) for d in data]
    except Exception as e:
        print("Ошибка поиска:", e)
        return []

# ===== Построение маршрута через OSRM =====
def get_route(lat1, lon1, lat2, lon2, mode="driving"):
    url = f"http://router.project-osrm.org/route/v1/{mode}/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("routes"):
            return None, None, None
        coords = [(lat, lon) for lon, lat in data["routes"][0]["geometry"]["coordinates"]]
        distance_m = data["routes"][0]["distance"]   # в метрах
        duration_s = data["routes"][0]["duration"]   # в секундах
        return coords, distance_m, duration_s
    except Exception as e:
        messagebox.showerror("Ошибка маршрута", str(e))
        return None, None, None

# ===== Отображение маршрута на карте =====
def show_map_with_route(point_a, point_b, name_a, name_b, mode="driving"):
    lat1, lon1 = point_a
    lat2, lon2 = point_b
    route, distance_m, duration_s = get_route(lat1, lon1, lat2, lon2, mode)
    if not route:
        return None, None

    m = folium.Map(location=[(lat1 + lat2)/2, (lon1 + lon2)/2], zoom_start=13)
    folium.Marker([lat1, lon1], popup=f"A: {name_a}", icon=folium.Icon(color='green')).add_to(m)
    folium.Marker([lat2, lon2], popup=f"B: {name_b}", icon=folium.Icon(color='red')).add_to(m)
    folium.PolyLine(route, color="blue", weight=5, opacity=0.8).add_to(m)

    map_path = "map_route.html"
    m.save(map_path)
    abs_path = os.path.abspath(map_path)
    webview.create_window("Маршрут", f"file:///{abs_path.replace(os.sep, '/')}", width=1000, height=700)
    webview.start()

    return distance_m, duration_s

# ===== GUI =====
class NavigatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Navigator 🚗🚶‍♂️🚴‍♂️")
        self.geometry("600x600")

        self.selected_a = None
        self.selected_b = None
        self.results_a = []
        self.results_b = []

        # Поле A
        ttk.Label(self, text="Откуда (A):").pack(anchor="w", padx=10, pady=5)
        self.entry_a = ttk.Entry(self)
        self.entry_a.pack(fill="x", padx=10)
        self.entry_a.bind("<KeyRelease>", self.update_suggestions_a)
        self.listbox_a = tk.Listbox(self, height=5)
        self.listbox_a.pack(fill="x", padx=10)
        self.listbox_a.bind("<<ListboxSelect>>", self.select_address_a)

        # Поле B
        ttk.Label(self, text="Куда (B):").pack(anchor="w", padx=10, pady=5)
        self.entry_b = ttk.Entry(self)
        self.entry_b.pack(fill="x", padx=10)
        self.entry_b.bind("<KeyRelease>", self.update_suggestions_b)
        self.listbox_b = tk.Listbox(self, height=5)
        self.listbox_b.pack(fill="x", padx=10)
        self.listbox_b.bind("<<ListboxSelect>>", self.select_address_b)

        # Выбор типа маршрута
        ttk.Label(self, text="Тип маршрута:").pack(anchor="w", padx=10, pady=5)
        self.mode_var = tk.StringVar(value="driving")
        mode_options = ["driving", "foot", "bike"]
        self.mode_menu = ttk.OptionMenu(self, self.mode_var, mode_options[0], *mode_options)
        self.mode_menu.pack(padx=10, pady=5)

        # Кнопка построения маршрута
        ttk.Button(self, text="🚗 Построить маршрут", command=self.build_route).pack(pady=15)

        # Вывод расстояния, времени и типа маршрута
        self.info_label = ttk.Label(self, text="", font=("Arial", 12), foreground="blue")
        self.info_label.pack(pady=10)

    # --------- Подсказки для A ---------
    def update_suggestions_a(self, event=None):
        query = self.entry_a.get().strip()
        self.listbox_a.delete(0, tk.END)
        self.results_a = search_addresses(query)
        for name, lat, lon in self.results_a:
            self.listbox_a.insert(tk.END, name)

    def select_address_a(self, event=None):
        if not self.listbox_a.curselection():
            return
        idx = self.listbox_a.curselection()[0]
        name, lat, lon = self.results_a[idx]
        self.selected_a = (lat, lon)
        self.entry_a.delete(0, tk.END)
        self.entry_a.insert(0, name)
        self.listbox_a.delete(0, tk.END)

    # --------- Подсказки для B ---------
    def update_suggestions_b(self, event=None):
        query = self.entry_b.get().strip()
        self.listbox_b.delete(0, tk.END)
        self.results_b = search_addresses(query)
        for name, lat, lon in self.results_b:
            self.listbox_b.insert(tk.END, name)

    def select_address_b(self, event=None):
        if not self.listbox_b.curselection():
            return
        idx = self.listbox_b.curselection()[0]
        name, lat, lon = self.results_b[idx]
        self.selected_b = (lat, lon)
        self.entry_b.delete(0, tk.END)
        self.entry_b.insert(0, name)
        self.listbox_b.delete(0, tk.END)

    # --------- Построение маршрута ---------
    def build_route(self):
        if not self.selected_a or not self.selected_b:
            messagebox.showwarning("Ошибка", "Выберите оба адреса (A и B)")
            return
        name_a = self.entry_a.get()
        name_b = self.entry_b.get()
        mode = self.mode_var.get()
        self.withdraw()
        distance_m, duration_s = show_map_with_route(self.selected_a, self.selected_b, name_a, name_b, mode)
        self.deiconify()

        # Отображение типа маршрута, расстояния и времени
        if distance_m is not None and duration_s is not None:
            distance_km = distance_m / 1000
            hours = int(duration_s // 3600)
            minutes = int((duration_s % 3600) // 60)
            mode_texts = {"driving": "На машине", "foot": "Пешком", "bike": "На велосипеде"}
            mode_text = mode_texts.get(mode, mode)
            self.info_label.config(
                text=f"Тип маршрута: {mode_text} | Расстояние: {distance_km:.2f} км | Время: {hours} ч {minutes} мин"
            )
        else:
            self.info_label.config(text="Маршрут не найден")

# ===== Запуск приложения =====
if __name__ == "__main__":
    app = NavigatorApp()
    app.mainloop()
