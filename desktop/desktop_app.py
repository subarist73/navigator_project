import sys
import io
import folium
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QPushButton, QComboBox, QListWidget
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWebChannel import QWebChannel

OSRM_URL = "http://router.project-osrm.org/route/v1"
GRAPH_HOPPER_KEY = "d2a4b8ac-1bde-4a7c-8021-1d8a15f6ea14"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

class MapBridge(QObject):
    pointClicked = Signal(float, float)
    @Slot(float, float)
    def onMapClick(self, lat, lon):
        self.pointClicked.emit(lat, lon)

class NavigatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Navigator 🚗🚶‍♂️🚴‍♂️")
        self.resize(1000, 700)

        self.point_a = None
        self.point_b = None
        self.next_point = "A"
        self.current_route_type = "driving"

        self.search_results_a = []
        self.search_results_b = []

        # Основной layout
        self.layout = QVBoxLayout(self)

        # --- Карта ---
        self.map_view = QWebEngineView()
        self.layout.addWidget(self.map_view, stretch=4)

        # --- Горизонтальный блок для полей и кнопок ---
        controls_layout = QHBoxLayout()

        # Колонка A
        col_a = QVBoxLayout()
        col_a.addWidget(QLabel("Точка A:"))
        self.entry_a = QLineEdit()
        col_a.addWidget(self.entry_a)
        self.list_a = QListWidget()
        col_a.addWidget(self.list_a)
        controls_layout.addLayout(col_a)

        # Колонка B
        col_b = QVBoxLayout()
        col_b.addWidget(QLabel("Точка B:"))
        self.entry_b = QLineEdit()
        col_b.addWidget(self.entry_b)
        self.list_b = QListWidget()
        col_b.addWidget(self.list_b)
        controls_layout.addLayout(col_b)

        # Колонка действий
        col_actions = QVBoxLayout()
        col_actions.addWidget(QLabel("Тип маршрута:"))
        self.route_type_combo = QComboBox()
        self.route_type_combo.addItems(["driving", "foot", "bike"])
        col_actions.addWidget(self.route_type_combo)

        self.btn_route = QPushButton("Построить маршрут")
        col_actions.addWidget(self.btn_route)
        self.btn_reset = QPushButton("Сбросить точки")
        col_actions.addWidget(self.btn_reset)

        self.info_label = QLabel("Кликните на карте или используйте поиск для выбора точек")
        col_actions.addWidget(self.info_label)
        col_actions.addStretch()

        controls_layout.addLayout(col_actions)

        self.layout.addLayout(controls_layout)

        # ===================== WebChannel =====================
        self.channel = QWebChannel()
        self.bridge = MapBridge()
        self.channel.registerObject("bridge", self.bridge)
        self.map_view.page().setWebChannel(self.channel)
        self.bridge.pointClicked.connect(self.handle_map_click)

        # ===================== Таймер поиска =====================
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.pending_field = None

        # ===================== События =====================
        self.entry_a.textChanged.connect(lambda: self.on_text_changed(self.entry_a, "a"))
        self.entry_b.textChanged.connect(lambda: self.on_text_changed(self.entry_b, "b"))
        self.list_a.itemClicked.connect(lambda item: self.select_point(item, "a"))
        self.list_b.itemClicked.connect(lambda item: self.select_point(item, "b"))
        self.route_type_combo.currentTextChanged.connect(self.change_route_type)
        self.btn_route.clicked.connect(self.build_route)
        self.btn_reset.clicked.connect(self.reset_points)

        self.update_map()

    # ===================== Методы =====================
    def change_route_type(self, text):
        self.current_route_type = text
        if self.point_a and self.point_b:
            self.build_route()

    def on_text_changed(self, entry, field):
        text = entry.text().strip()
        self.pending_field = field
        self.search_timer.stop()
        if len(text) >= 3:
            self.search_timer.start(500)

    def perform_search(self):
        field = self.pending_field
        entry = self.entry_a if field == "a" else self.entry_b
        list_widget = self.list_a if field == "a" else self.list_b
        query = entry.text().strip()
        if len(query) < 3:
            list_widget.clear()
            return
        headers = {"User-Agent": "NavigatorApp/1.0"}
        params = {"q": query, "format": "json", "addressdetails": 1, "limit": 5}
        try:
            r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=5)
            r.raise_for_status()
            data = r.json()
            results = [(d["display_name"], float(d["lat"]), float(d["lon"])) for d in data]
            if field == "a":
                self.search_results_a = results
            else:
                self.search_results_b = results
            list_widget.clear()
            for name, _, _ in results:
                list_widget.addItem(name)
        except Exception as e:
            list_widget.clear()
            print("Ошибка поиска:", e)

    def select_point(self, item, field):
        name = item.text()
        if field == "a":
            coords = next(((lat, lon) for n, lat, lon in self.search_results_a if n == name), None)
            self.point_a = coords
            self.entry_a.setText(name)
            self.list_a.clear()
            self.next_point = "B"
        else:
            coords = next(((lat, lon) for n, lat, lon in self.search_results_b if n == name), None)
            self.point_b = coords
            self.entry_b.setText(name)
            self.list_b.clear()
            self.next_point = None
            self.build_route()
        self.update_map()

    def handle_map_click(self, lat, lon):
        if self.next_point == "A":
            self.point_a = (lat, lon)
            self.entry_a.setText(f"{lat:.6f}, {lon:.6f}")
            self.info_label.setText("Точка A выбрана. Выберите точку B")
            self.next_point = "B"
        elif self.next_point == "B":
            self.point_b = (lat, lon)
            self.entry_b.setText(f"{lat:.6f}, {lon:.6f}")
            self.info_label.setText("Точка B выбрана. Маршрут строится автоматически")
            self.next_point = None
            self.build_route()
        self.update_map()

    def reset_points(self):
        self.point_a = None
        self.point_b = None
        self.entry_a.clear()
        self.entry_b.clear()
        self.list_a.clear()
        self.list_b.clear()
        self.next_point = "A"
        self.info_label.setText("Кликните на карте или используйте поиск для выбора точек")
        self.update_map()

    def get_route(self, lat1, lon1, lat2, lon2):
        if self.current_route_type == "foot":
            url = "https://graphhopper.com/api/1/route"
            params = {
                "point": [f"{lat1},{lon1}", f"{lat2},{lon2}"],
                "vehicle": "foot",
                "locale": "ru",
                "calc_points": "true",
                "points_encoded": "false",
                "key": GRAPH_HOPPER_KEY
            }
            try:
                r = requests.get(url, params=params, timeout=10)
                r.raise_for_status()
                data = r.json()
                path = data["paths"][0]
                coords = [(lat, lon) for lon, lat in path["points"]["coordinates"]]
                return coords
            except Exception as e:
                print("GraphHopper error:", e)
                mode = "foot"
        else:
            mode = "car" if self.current_route_type == "driving" else "bike"

        url = f"{OSRM_URL}/{mode}/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        try:
            r = requests.get(url, timeout=10).json()
            route = r["routes"][0]
            coords = [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
            return coords
        except Exception as e:
            print("OSRM error:", e)
            return None

    def build_route(self):
        if self.point_a and self.point_b:
            coords = self.get_route(*self.point_a, *self.point_b)
            self.update_map(route_coords=coords)

    def update_map(self, route_coords=None):
        center = self.point_a or (55.751244, 37.618423)
        m = folium.Map(location=center, zoom_start=12)
        if self.point_a:
            folium.Marker(self.point_a, popup="A", icon=folium.Icon(color="green")).add_to(m)
        if self.point_b:
            folium.Marker(self.point_b, popup="B", icon=folium.Icon(color="red")).add_to(m)
        if route_coords:
            folium.PolyLine(route_coords, color="blue", weight=5).add_to(m)

        data = io.BytesIO()
        m.save(data, close_file=False)
        html = data.getvalue().decode()

        import re
        map_var = "map"
        mobj = re.search(r"var (map_[a-z0-9]+) = L.map", html)
        if mobj:
            map_var = mobj.group(1)

        inject = f"""
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function() {{
    var mapObj = window.{map_var};
    new QWebChannel(qt.webChannelTransport, function(channel) {{
        window.bridge = channel.objects.bridge;
        mapObj.on('click', function(e) {{
            window.bridge.onMapClick(e.latlng.lat, e.latlng.lng);
        }});
    }});
}});
</script>
"""
        html = html.replace("</body>", inject + "</body>")
        self.map_view.setHtml(html)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = NavigatorApp()
    win.show()
    sys.exit(app.exec())
