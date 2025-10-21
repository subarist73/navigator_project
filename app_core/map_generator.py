# app_core/map_generator.py
import folium
import os
from datetime import datetime

def generate_map(center=(55.751244, 37.618423), markers=None, out_html=None, zoom_start=13):
    """
    Создаёт folium карту и сохраняет в out_html.
    center: (lat, lon)
    markers: list of dicts: {'lat':..., 'lon':..., 'popup': '...'}
    """
    if markers is None:
        markers = []

    m = folium.Map(location=center, zoom_start=zoom_start, control_scale=True)
    for mk in markers:
        folium.Marker(location=(mk['lat'], mk['lon']), popup=mk.get('popup','')).add_to(m)

    if out_html is None:
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        out_html = os.path.join(os.getcwd(), f'folium_map_{ts}.html')

    m.save(out_html)
    return out_html

if __name__ == "__main__":
    # тест
    html = generate_map(center=(59.93,30.34),
                        markers=[{'lat':59.93,'lon':30.34,'popup':'Start'},
                                 {'lat':59.94,'lon':30.35,'popup':'Dest'}])
    print("Saved map to", html)
