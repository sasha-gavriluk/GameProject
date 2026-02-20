import asyncio

from gui.screen.BaseScreen import BaseScreen
from gui.NetworkBridge import net
from gui.config.Configs import VisualConfig
from gui.utils.Responsive import bind_responsive_width, bind_scaled_property


class RoomEntryScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        self.ui = ui_manager
        self.controller = controller
        self.setup_ui()
        self.add_widget(self.ui.root)

    def setup_ui(self):
        self.ui.add("room_anchor", "AnchorLayout", anchor_x='center', anchor_y='center')
        self.ui.add(
            "room_box",
            "BoxLayout",
            parent="room_anchor",
            orientation="vertical",
            spacing=VisualConfig.sdp(20),
            size_hint=(None, None),
            width=VisualConfig.sdp(300),
        )

        self.ui.add("room_title", "TitleLabel", parent="room_box", text="Кімната")
        self.ui.add("room_id_input", "GameTextInput", parent="room_box", hint_text="Введіть ID кімнати")
        self.ui.add("btn_join_room", "MenuButton", parent="room_box", text="Приєднатися")
        self.ui.add("btn_create_room", "MenuButton", parent="room_box", text="Створити кімнату")
        self.ui.add("btn_back_room", "MenuButton", parent="room_box", text="Назад")

        self.ui.set_action("btn_join_room", "on_release", self.join_room)
        self.ui.set_action("btn_create_room", "on_release", self.create_room)
        self.ui.set_action("btn_back_room", "on_release", lambda *_: self.controller.switch_screen('main_menu'))

        self.ui.build()

        box = self.ui.registry["room_box"]
        box.bind(minimum_height=box.setter('height'))
        bind_scaled_property(box, "spacing", 20)
        bind_responsive_width(box, max_width=360, ratio=0.85, min_width=260)

    def on_enter(self, *args):
        self.ui.registry["room_id_input"].text = ""

    def create_room(self, *_):
        asyncio.create_task(self._async_create_room())

    async def _async_create_room(self):
        success, room_id = await net.create_room()
        if success and self.controller:
            self.controller.switch_screen('lobby', room_id=room_id)

    def join_room(self, *_):
        room_id = self.ui.registry["room_id_input"].text.strip()
        if room_id:
            asyncio.create_task(self._async_join_room(room_id))

    async def _async_join_room(self, room_id):
        success, _msg = await net.join_room(room_id)
        if success and self.controller:
            self.controller.switch_screen('lobby', room_id=room_id)
