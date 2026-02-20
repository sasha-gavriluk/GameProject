from kivy.core.window import Window

from gui.config.Configs import VisualConfig


def bind_scaled_property(widget, attr, base_value):
    def update(*_):
        setattr(widget, attr, VisualConfig.sdp(base_value))
    update()
    Window.bind(size=lambda *_: update())


def bind_scaled_padding(widget, base_value):
    def update(*_):
        pad = VisualConfig.sdp(base_value)
        widget.padding = [pad, pad, pad, pad]
    update()
    Window.bind(size=lambda *_: update())


def bind_responsive_width(widget, max_width, ratio=0.85, min_width=None):
    def update(*_):
        target = min(VisualConfig.sdp(max_width), Window.width * ratio)
        if min_width is not None:
            target = max(VisualConfig.sdp(min_width), target)
        widget.width = target
    update()
    Window.bind(size=lambda *_: update())
