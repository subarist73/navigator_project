# mobile/main.py
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
import webbrowser
from app_core.map_generator import generate_map
import os

class Root(BoxLayout):
    def show_map(self, *args):
        out = generate_map(center=(55.751244,37.618423),
                           markers=[{'lat':55.75,'lon':37.62,'popup':'Moscow'}],
                           out_html=os.path.join(os.getcwd(),'map_mobile.html'))
        # Попробуем открыть в системном браузере (работает и на Android)
        webbrowser.open('file://' + out)

class MyApp(App):
    def build(self):
        root = Root(orientation='vertical')
        btn = Button(text='Generate & Open map', size_hint=(1, 0.1))
        btn.bind(on_release=root.show_map)
        root.add_widget(btn)
        return root

if __name__ == '__main__':
    MyApp().run()
