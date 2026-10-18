"""GTK 3 window and tray icon for CouchPad on KDE Plasma."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import threading
from pathlib import Path
from typing import Callable

from . import discovery
from .config import STEAM_START, config_path, load, save_basic_settings
from .control import request
from .system import host_environment


LOG = logging.getLogger(__name__)
ICON = Path(__file__).resolve().parent / "assets" / "couchpad.svg"

CSS = b"""
window { background: #0d1018; color: #e9ebf2; }
.sidebar { background: #10131c; border-right: 1px solid #292e3e; padding: 18px 12px; }
.brand { color: #f3f4f8; font-size: 21px; font-weight: bold; }
.sidebar-caption { color: #8991a5; font-size: 13px; }
button.nav-button { background: transparent; border: 0; box-shadow: none; color: #929aaf; min-height: 38px; padding: 6px 10px; border-radius: 9px; font-size: 14px; }
button.nav-button:hover { background: #1b2030; color: #f1f3f9; }
button.nav-button.nav-active { background: #202638; color: #f3f5fa; font-weight: bold; }
button.nav-button.nav-active image { color: #31cf9a; }
button.sidebar-action { background: transparent; border: 1px solid #293044; color: #c9ceda; min-height: 36px; border-radius: 9px; }
button.sidebar-action:hover { background: #202638; }
.card, .stat-card { background: #171b27; border: 1px solid #293044; border-radius: 14px; padding: 14px; }
.stat-card { padding: 12px; }
.section-title { color: #ecedf4; font-size: 16px; font-weight: bold; }
.card-icon-badge { background: #202336; border-radius: 10px; padding: 7px; }
.field-title, .muted { color: #939bb0; font-size: 12px; }
.field-value { color: #eceef5; font-size: 14px; font-weight: 600; }
.stat-value { color: #eef0f6; font-size: 16px; font-weight: bold; }
.stat-subvalue { color: #818aa0; font-size: 12px; }
.status-pill { background: #302433; color: #f3bd80; border-radius: 16px; padding: 5px 11px; font-weight: bold; }
.status-idle { background: #302433; color: #f3bd80; }
.automation-banner { border-radius: 14px; padding: 4px 0; background: transparent; border: 0; }
.automation-banner.automation-on, .automation-banner.automation-off { background: transparent; border: 0; }
.automation-title { color: #f2f3f8; font-size: 22px; font-weight: bold; }
.automation-description { color: #a0a8b8; font-size: 14px; }
.feedback { color: #efb274; font-size: 13px; }
button.automation-action { min-height: 46px; min-width: 170px; font-size: 15px; font-weight: bold; border-radius: 11px; }
button.automation-action.automation-enable, button.primary-button { background: #31cf9a; color: #081b19; border: 1px solid #31cf9a; font-weight: bold; border-radius: 9px; min-height: 36px; }
button.automation-action.automation-enable:hover, button.primary-button:hover { background: #4bdfaf; }
button.automation-action.automation-disable { background: #74445a; color: #fff2f4; border: 1px solid #9f5b73; }
button.automation-action.automation-disable:hover { background: #915268; }
button.save-button { background: #7f68ee; color: white; border: 1px solid #7f68ee; font-weight: bold; min-height: 37px; border-radius: 9px; }
button.save-button:hover { background: #947ffa; }
button.outline-button { background: transparent; border: 1px solid #343b52; color: #cbd0dc; min-height: 36px; border-radius: 9px; }
button.outline-button:hover { background: #242a3a; }
button.chooser-button { background: transparent; border: 1px dashed #434b62; color: #efb274; min-height: 36px; border-radius: 9px; }
button.chooser-button:hover { background: #242538; }
.display-map { background: #10131c; border-radius: 12px; padding: 10px; }
.screen-current { background: #172620; border: 2px solid #31cf9a; border-radius: 9px; padding: 11px; }
.screen-target { background: #171b27; border: 2px dashed #46506a; border-radius: 9px; padding: 11px; }
.screen-arrow { color: #818ba2; font-size: 27px; }
.mode-bar { background: #10131c; border-radius: 9px; padding: 3px; }
button.mode-button { background: transparent; border: 0; box-shadow: none; color: #959eb3; min-height: 32px; }
button.mode-button:checked { background: #293149; color: #f0f2fa; border-radius: 10px; font-weight: bold; }
button, combobox, spinbutton, entry { min-height: 32px; }
entry, spinbutton { background: #252a39; color: #e9ebf2; border: 1px solid #333b50; border-radius: 8px; }
combobox button { background: #252a39; color: #e9ebf2; border: 1px solid #333b50; border-radius: 8px; }
switch:checked { background: #31cf9a; }
"""


def main() -> None:
    os.environ.setdefault("GDK_BACKEND", "x11")
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, GLib, Gtk

    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )

    def styled_label(text: str, style: str, wrap: bool = False) -> Gtk.Label:
        item = Gtk.Label(label=text)
        item.set_xalign(0)
        item.set_line_wrap(wrap)
        item.get_style_context().add_class(style)
        return item

    def card_icon(name: str, size: int) -> Gtk.Image:
        from gi.repository import GdkPixbuf

        path = ICON.parent / f"card-{name}.svg"
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), size, size, True)
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        image.set_valign(Gtk.Align.CENTER)
        return image

    def titled_row(title: str, style: str, icon: str) -> Gtk.Box:
        row = Gtk.Box(spacing=10)
        row.set_valign(Gtk.Align.CENTER)
        image = card_icon(icon, 18 if style == "section-title" else 16)
        if style == "section-title":
            badge = Gtk.Box()
            badge.get_style_context().add_class("card-icon-badge")
            badge.set_halign(Gtk.Align.START)
            badge.set_valign(Gtk.Align.CENTER)
            badge.pack_start(image, False, False, 0)
            row.pack_start(badge, False, False, 0)
        else:
            row.pack_start(image, False, False, 0)
        row.pack_start(styled_label(title, style), True, True, 0)
        return row

    def card(title: str, icon: str) -> tuple[Gtk.Box, Gtk.Box]:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        outer.get_style_context().add_class("card")
        outer.pack_start(titled_row(title, "section-title", icon), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        outer.pack_start(body, True, True, 0)
        return outer, body

    def field(container: Gtk.Box, title: str, value: Gtk.Label) -> None:
        group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        group.pack_start(styled_label(title.upper(), "field-title"), False, False, 0)
        group.pack_start(value, False, False, 0)
        container.pack_start(group, False, False, 0)

    class Tray:
        def __init__(self) -> None:
            self.busy = False
            self.online = False
            self._last_service_state = {}
            self.active = False
            self.scanning = False
            self.saving_preferences = False
            self._setting_launchers = False
            self._populating_settings = False
            self._autosave_source = 0
            self.save_feedback = []
            self.detected_gamepad = ""
            self.detected_screen = ""
            self.config = load()
            self.enabled = self.config.enabled
            portable = bool(os.environ.get("COUCHPAD_APPIMAGE"))
            self.window = Gtk.Window(title="CouchPad Beta" if portable else "CouchPad")
            self.window.set_default_size(1420, 900)
            self.window.set_size_request(1100, 740)
            self.window.connect("delete-event", self.hide_window)
            self.window.set_icon_from_file(str(ICON))
            self.scroll = Gtk.ScrolledWindow()
            self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            self.window.add(self.scroll)
            self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            self.content.set_margin_top(14)
            self.content.set_margin_bottom(14)
            self.content.set_margin_start(16)
            self.content.set_margin_end(16)
            self.scroll.add(self.content)

            self.automation_banner = Gtk.Box(spacing=18)
            self.automation_banner.get_style_context().add_class("automation-banner")
            identity = Gtk.Box(spacing=12)
            logo = Gtk.Image.new_from_file(str(ICON))
            logo.set_pixel_size(48)
            identity.pack_start(logo, False, False, 0)
            identity_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            self.automation_title = styled_label("CouchPad Beta" if portable else "CouchPad", "brand")
            self.automation_description = styled_label(
                "Espaço de jogo automático", "automation-description", True,
            )
            identity_text.pack_start(self.automation_title, False, False, 0)
            identity_text.pack_start(self.automation_description, False, False, 0)
            identity.pack_start(identity_text, False, False, 0)
            self.automation_banner.pack_start(identity, True, True, 0)
            self.badge = styled_label("Conectando…", "status-pill")
            self.badge.set_halign(Gtk.Align.START)
            self.automation_banner.pack_start(self.badge, False, False, 0)
            self.status = styled_label("Verificando serviço…", "muted", True)
            self.message = styled_label("", "feedback", True)
            self.service_button = Gtk.Button(label="Ativar CouchPad")
            self.service_button.get_style_context().add_class("automation-action")
            self.service_button.set_valign(Gtk.Align.CENTER)
            self.service_button.connect("clicked", self.toggle_enabled)
            self.automation_banner.pack_end(self.service_button, False, False, 0)
            self.content.pack_start(self.automation_banner, False, False, 0)
            header_status = Gtk.Box(spacing=10)
            header_status.pack_start(self.status, True, True, 0)
            header_status.pack_end(self.message, False, False, 0)
            self.content.pack_start(header_status, False, False, 0)

            stats = Gtk.Grid(column_spacing=10)
            stats.set_column_homogeneous(True)
            self.content.pack_start(stats, False, False, 0)

            def stat_card(title: str, icon: str) -> tuple[Gtk.Box, Gtk.Label, Gtk.Label]:
                outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                outer.get_style_context().add_class("stat-card")
                outer.pack_start(titled_row(title, "field-title", icon), False, False, 0)
                value = styled_label("—", "stat-value", True)
                subvalue = styled_label("", "stat-subvalue", True)
                outer.pack_start(value, False, False, 0)
                outer.pack_start(subvalue, False, False, 0)
                return outer, value, subvalue

            controller_stat, self.summary_gamepad, self.summary_gamepad_detail = stat_card(
                "Controle", "gamepad-green",
            )
            screen_stat, self.summary_screen, self.summary_screen_detail = stat_card(
                "Tela ativa", "display-green",
            )
            audio_stat, self.summary_audio, self.summary_audio_detail = stat_card(
                "Áudio", "audio-green",
            )
            launcher_stat, self.summary_launcher, self.summary_launcher_detail = stat_card(
                "Inicializador", "launcher-green",
            )
            for column, item in enumerate((controller_stat, screen_stat, audio_stat, launcher_stat)):
                stats.attach(item, column, 0, 1, 1)

            dashboard = Gtk.Grid(column_spacing=14, row_spacing=14)
            dashboard.set_column_homogeneous(True)
            self.content.pack_start(dashboard, False, False, 0)

            display, body = card("Tela de jogo", "display-green")
            dashboard.attach(display, 0, 0, 1, 1)
            map_box = Gtk.Box(spacing=10)
            map_box.get_style_context().add_class("display-map")
            map_box.set_halign(Gtk.Align.FILL)
            current_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            current_box.get_style_context().add_class("screen-current")
            current_box.set_halign(Gtk.Align.FILL)
            self.current_display = styled_label("—", "field-value", True)
            current_box.pack_start(self.current_display, False, False, 0)
            self.current_map_caption = styled_label("Atual", "stat-subvalue")
            current_box.pack_start(self.current_map_caption, False, False, 0)
            map_box.pack_start(current_box, True, True, 0)
            arrow = styled_label("→", "screen-arrow")
            arrow.set_valign(Gtk.Align.CENTER)
            map_box.pack_start(arrow, False, False, 0)
            target_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            target_box.get_style_context().add_class("screen-target")
            self.target_display = styled_label(self.config.tv_output, "field-value", True)
            target_box.pack_start(self.target_display, False, False, 0)
            self.target_output_label = styled_label(self.config.tv_output, "stat-subvalue")
            target_box.pack_start(self.target_output_label, False, False, 0)
            map_box.pack_start(target_box, True, True, 0)
            body.pack_start(map_box, False, False, 0)
            body.pack_start(styled_label("TV de destino", "field-title"), False, False, 0)
            self.tv_chooser = Gtk.ComboBoxText()
            self.tv_chooser.connect("changed", self.tv_choice_changed)
            body.pack_start(self.tv_chooser, False, False, 0)
            display_buttons = Gtk.Box(spacing=10)
            self.activate_button = Gtk.Button(label="Ativar TV")
            self.activate_button.get_style_context().add_class("primary-button")
            self.activate_button.connect("clicked", lambda *_: self.send("activate"))
            display_buttons.pack_start(self.activate_button, True, True, 0)
            self.restore_button = Gtk.Button(label="Restaurar")
            self.restore_button.get_style_context().add_class("outline-button")
            self.restore_button.connect("clicked", lambda *_: self.send("restore"))
            display_buttons.pack_start(self.restore_button, True, True, 0)
            body.pack_start(display_buttons, False, False, 0)
            body.pack_start(styled_label("Modo de vídeo", "field-title"), False, False, 0)
            mode_bar = Gtk.Box(spacing=4)
            mode_bar.get_style_context().add_class("mode-bar")
            self.mode_buttons = {}
            for value, label in (("tv-only", "Somente TV"), ("extend", "Estender"),
                                 ("mirror", "Espelhar")):
                button = Gtk.ToggleButton(label=label)
                button.get_style_context().add_class("mode-button")
                button.connect("toggled", self.mode_toggled, value)
                mode_bar.pack_start(button, True, True, 0)
                self.mode_buttons[value] = button
            body.pack_start(mode_bar, False, False, 0)
            display_feedback = styled_label("Alterações salvas automaticamente", "feedback", True)
            body.pack_start(display_feedback, False, False, 0)
            self.save_feedback.append(display_feedback)

            launchers, body = card("Inicializadores", "launcher-purple")
            dashboard.attach(launchers, 2, 0, 1, 2)
            steam_row = Gtk.Box(spacing=8)
            steam_row.pack_start(styled_label("Steam Big Picture", "field-value"), True, True, 0)
            self.steam = Gtk.Switch()
            self.steam.set_valign(Gtk.Align.CENTER)
            steam_row.pack_end(self.steam, False, False, 0)
            body.pack_start(steam_row, False, False, 0)
            other_row = Gtk.Box(spacing=8)
            other_row.pack_start(styled_label("Outro programa", "field-value"), True, True, 0)
            self.custom_launcher_switch = Gtk.Switch()
            self.custom_launcher_switch.set_valign(Gtk.Align.CENTER)
            other_row.pack_end(self.custom_launcher_switch, False, False, 0)
            body.pack_start(other_row, False, False, 0)
            close_row = Gtk.Box(spacing=8)
            close_row.pack_start(styled_label("Fechar outro programa ao restaurar", "muted"), True, True, 0)
            self.custom_close_switch = Gtk.Switch()
            self.custom_close_switch.set_valign(Gtk.Align.CENTER)
            close_row.pack_end(self.custom_close_switch, False, False, 0)
            body.pack_start(close_row, False, False, 0)
            self.custom_launcher_path = Gtk.Entry()
            self.custom_launcher_path.set_editable(False)
            self.custom_launcher_path.set_placeholder_text("Nenhum programa escolhido")
            body.pack_start(self.custom_launcher_path, False, False, 0)
            self.custom_launcher_args = Gtk.Entry()
            self.custom_launcher_args.set_placeholder_text("Argumentos (ex.: --big-picture para Hydra)")
            body.pack_start(self.custom_launcher_args, False, False, 0)
            self.choose_launcher = Gtk.Button(label="Escolher programa…")
            self.choose_launcher.get_style_context().add_class("chooser-button")
            self.choose_launcher.connect("clicked", self.choose_custom_launcher)
            body.pack_start(self.choose_launcher, False, False, 0)
            self.launcher_feedback = styled_label("Alterações salvas automaticamente", "feedback", True)
            body.pack_start(self.launcher_feedback, False, False, 0)
            self.save_feedback.append(self.launcher_feedback)
            body.pack_start(styled_label(
                "Ao fechar, o CouchPad sinaliza apenas o processo que iniciou; jogos permanecem abertos.",
                "muted", True,
            ), False, False, 0)

            settings, body = card("Atrasos", "clock-orange")
            dashboard.attach(settings, 0, 1, 1, 1)
            for label, attribute in (("Ao conectar", "connect_delay"),
                                     ("Ao desconectar", "disconnect_delay")):
                row = Gtk.Box(spacing=12)
                row.pack_start(styled_label(label, "field-title"), True, True, 0)
                spin = Gtk.SpinButton.new_with_range(0, 300, 0.5)
                spin.set_digits(1)
                spin.set_numeric(True)
                row.pack_end(spin, False, False, 0)
                body.pack_start(row, False, False, 0)
                setattr(self, attribute, spin)
            settings_feedback = styled_label("Alterações salvas automaticamente", "feedback", True)
            body.pack_end(settings_feedback, False, False, 0)
            self.save_feedback.append(settings_feedback)

            gamepad, body = card("Controle principal e ativação", "gamepad-purple")
            dashboard.attach(gamepad, 1, 0, 1, 1)
            self.controller = styled_label("Desconectado", "field-value", True)
            field(body, "Controle detectado", self.controller)
            body.pack_start(styled_label("Controle que ativa a TV", "field-title"), False, False, 0)
            self.gamepad_chooser = Gtk.ComboBoxText()
            body.pack_start(self.gamepad_chooser, False, False, 0)
            self.gamepad_filter = styled_label("—", "muted", True)
            body.pack_start(self.gamepad_filter, False, False, 0)
            self.combo_value = styled_label("Ao conectar o controle", "field-value", True)
            field(body, "Combinação de ativação", self.combo_value)
            combo_edit = Gtk.Button(label="Editar combinação")
            combo_edit.get_style_context().add_class("outline-button")
            combo_edit.connect("clicked", self.open_config)
            body.pack_start(combo_edit, False, False, 0)
            control_feedback = styled_label("Alterações salvas automaticamente", "feedback", True)
            body.pack_start(control_feedback, False, False, 0)
            self.save_feedback.append(control_feedback)

            transition, body = card("Tela e áudio", "audio-green")
            dashboard.attach(transition, 1, 1, 1, 1)
            self.audio_target = styled_label("—", "field-value", True)
            field(body, "Saída detectada", self.audio_target)
            body.pack_start(styled_label("Saída de áudio para a TV", "field-title"), False, False, 0)
            self.audio_chooser = Gtk.ComboBoxText()
            self.audio_chooser.connect("changed", self.audio_choice_changed)
            body.pack_start(self.audio_chooser, False, False, 0)
            self.audio_manual = Gtk.Entry()
            self.audio_manual.set_placeholder_text("Ou informe o nome da saída de áudio")
            body.pack_start(self.audio_manual, False, False, 0)
            body.pack_start(styled_label(
                "A saída HDMI pode aparecer somente depois que a TV for ativada. "
                "Nesse caso, use Automático ou mantenha a saída já configurada.",
                "muted", True,
            ), False, False, 0)
            audio_feedback = styled_label("Alterações salvas automaticamente", "feedback", True)
            body.pack_start(audio_feedback, False, False, 0)
            self.save_feedback.append(audio_feedback)

            footer = Gtk.Box(spacing=10)
            footer.pack_start(Gtk.Box(), True, True, 0)
            advanced = Gtk.Button(label="Configuração completa")
            advanced.get_style_context().add_class("outline-button")
            advanced.connect("clicked", self.open_config)
            footer.pack_end(advanced, False, False, 0)
            detect = Gtk.Button(label="Detectar dispositivos")
            detect.get_style_context().add_class("outline-button")
            detect.connect("clicked", lambda *_: self.scan_devices())
            footer.pack_end(detect, False, False, 0)
            self.content.pack_start(footer, False, False, 0)
            self.tv_choices = {}
            self.gamepad_choices = {}
            self.last_scan = {"displays": [], "audio": [], "gamepads": []}
            self._updating_devices = False
            self.populate_settings()

            self.icon = Gtk.StatusIcon.new_from_file(str(ICON))
            self.icon.set_visible(True)
            self.icon.set_tooltip_text("CouchPad")
            self.icon.connect("activate", lambda *_: self.show_window())
            self.icon.connect("popup-menu", self.popup_menu)
            self.menu = Gtk.Menu()
            self.toggle_item = Gtk.MenuItem(label="Desativar CouchPad")
            self.toggle_item.connect("activate", self.toggle_enabled)
            self.menu.append(self.toggle_item)
            self.menu.append(Gtk.SeparatorMenuItem())
            self.menu_cancel = Gtk.MenuItem(label="Cancelar troca para TV")
            self.menu_cancel.connect("activate", lambda *_: self.send("cancel"))
            self.menu.append(self.menu_cancel)
            for text, callback in (("Abrir CouchPad", lambda *_: self.show_window()),
                                   ("Ativar TV", lambda *_: self.send("activate")),
                                   ("Restaurar desktop", lambda *_: self.send("restore"))):
                item = Gtk.MenuItem(label=text)
                item.connect("activate", callback)
                self.menu.append(item)
                if text == "Ativar TV":
                    self.menu_activate = item
                elif text == "Restaurar desktop":
                    self.menu_restore = item
            self.menu.append(Gtk.SeparatorMenuItem())
            quit_item = Gtk.MenuItem(label="Encerrar CouchPad" if
                                    os.environ.get("COUCHPAD_OWNS_MONITOR") == "1" else "Fechar interface")
            quit_item.connect("activate", lambda *_: Gtk.main_quit())
            self.menu.append(quit_item)
            self.menu.show_all()
            self.window.show_all()
            GLib.timeout_add_seconds(2, self.refresh)
            GLib.timeout_add_seconds(10, self.periodic_scan)
            GLib.timeout_add_seconds(5, self.report_icon)
            self.refresh()
            self.scan_devices()

        def report_icon(self) -> bool:
            LOG.info("Ícone integrado à bandeja: %s", self.icon.is_embedded())
            return False

        def periodic_scan(self) -> bool:
            if not self.busy:
                self.scan_devices()
            return True

        def scan_devices(self) -> None:
            if self.scanning:
                return
            self.scanning = True
            config = self.config

            def worker() -> None:
                result = discovery.scan(config)
                GLib.idle_add(self.show_devices, result)

            threading.Thread(target=worker, daemon=True).start()

        def update_device_choices(self, result: dict[str, object], reset: bool = False) -> None:
            previous_tv = None if reset else self.tv_chooser.get_active_id()
            previous_gamepad = None if reset else self.gamepad_chooser.get_active_id()
            previous_audio = None if reset else self.audio_chooser.get_active_id()
            old_gamepads = self.gamepad_choices
            self._updating_devices = True
            try:
                self.tv_chooser.remove_all()
                displays_found = result.get("displays", [])
                self.tv_choices = {
                    str(item["output"]): item for item in displays_found
                    if isinstance(item, dict) and item.get("connected")
                    and item.get("output") != self.config.desktop_output
                }
                if self.config.tv_output not in self.tv_choices:
                    self.tv_choices[self.config.tv_output] = {
                        "output": self.config.tv_output, "connected": False,
                        "label": f"{self.config.tv_output} — desconectada",
                        "edid_sha256": self.config.tv_edid_sha256,
                    }
                for output, item in self.tv_choices.items():
                    self.tv_chooser.append(output, str(item.get("label") or output))
                self.tv_chooser.set_active_id(previous_tv if previous_tv in self.tv_choices
                                              else self.config.tv_output)

                self.gamepad_chooser.remove_all()
                self.gamepad_chooser.append("__any__", "Qualquer controle")
                gamepads_found = result.get("gamepads", [])
                self.gamepad_choices = {
                    str(item["path"]): item for item in gamepads_found
                    if isinstance(item, dict) and item.get("path")
                }
                if (previous_gamepad in old_gamepads and
                        previous_gamepad not in self.gamepad_choices):
                    self.gamepad_choices[previous_gamepad] = old_gamepads[previous_gamepad]
                for path, item in self.gamepad_choices.items():
                    identifier = str(item.get("uniq") or Path(path).name)
                    model = str(item["model"])
                    if len(model) > 20:
                        model = model[:19] + "…"
                    label = (f"{model} · {item['vendor_id']}:{item['product_id']}"
                             f" · {identifier}")
                    if path not in {x.get("path") for x in gamepads_found if isinstance(x, dict)}:
                        label += " (desconectado)"
                    self.gamepad_chooser.append(path, label)
                if self.config.gamepad_name:
                    configured_id = (f" · {self.config.gamepad_vendor_id}:{self.config.gamepad_product_id}"
                                     if self.config.gamepad_vendor_id else "")
                    configured_name = self.config.gamepad_name
                    if len(configured_name) > 20:
                        configured_name = configured_name[:19] + "…"
                    self.gamepad_chooser.append("__configured__",
                                                f"{configured_name}{configured_id} (salvo)")
                gamepad_selection = (previous_gamepad if previous_gamepad in self.gamepad_choices
                                     or previous_gamepad in ("__any__", "__configured__") else
                                     ("__configured__" if self.config.gamepad_name else "__any__"))
                self.gamepad_chooser.set_active_id(gamepad_selection)

                self.audio_chooser.remove_all()
                self.audio_chooser.append("__auto__", "Automático — identificar a saída da TV")
                sinks_found = result.get("audio", [])
                audio_choices = {
                    str(item["name"]): item for item in sinks_found
                    if isinstance(item, dict) and item.get("name")
                }
                for name, item in audio_choices.items():
                    label = f"{item.get('description') or name} · {name.rsplit('.', 1)[-1]}"
                    self.audio_chooser.append(name, label[:36] + ("…" if len(label) > 36 else ""))
                for name in (self.config.tv_sink, previous_audio):
                    if name and name != "__auto__" and name not in audio_choices:
                        short_name = name.removeprefix("alsa_output.")
                        if len(short_name) > 38:
                            short_name = short_name[:18] + "…" + short_name[-18:]
                        self.audio_chooser.append(name, f"{short_name} (indisponível)")
                        audio_choices[name] = {"name": name}
                selected_audio = previous_audio if previous_audio in audio_choices or previous_audio == "__auto__" else (
                    self.config.tv_sink or "__auto__")
                self.audio_chooser.set_active_id(selected_audio)
                self.audio_chooser.set_tooltip_text(selected_audio if selected_audio != "__auto__" else None)
            finally:
                self._updating_devices = False
            self.update_target_preview()

        def update_target_preview(self) -> None:
            output = self.tv_chooser.get_active_id() or self.config.tv_output
            item = self.tv_choices.get(output, {})
            self.target_display.set_text(str(item.get("label") or output))
            self.target_output_label.set_text(output)

        def tv_choice_changed(self, *_args: object) -> None:
            if self._updating_devices:
                return
            self.update_target_preview()
            if self.tv_chooser.get_active_id() != self.config.tv_output:
                self.audio_chooser.set_active_id("__auto__")
                self.audio_manual.set_text("")
            self.message.set_text("Ajuste de TV em andamento…")

        def audio_choice_changed(self, *_args: object) -> None:
            if not self._updating_devices:
                self.audio_manual.set_text("")
                selected = self.audio_chooser.get_active_id()
                self.audio_chooser.set_tooltip_text(selected if selected != "__auto__" else None)

        def show_devices(self, result: dict[str, object]) -> bool:
            self.scanning = False
            self.last_scan = result
            self.update_device_choices(result)
            tv = result.get("tv")
            if isinstance(tv, dict) and tv.get("connected"):
                self.detected_screen = str(tv.get("label") or tv["output"])
                if tv.get("configured_match") is False:
                    self.target_display.set_text("TV diferente da configurada — troca bloqueada")
                else:
                    self.target_display.set_text(self.detected_screen)
            else:
                self.detected_screen = ""
                self.target_display.set_text(f"{self.config.tv_output} — desconectada")
            chosen = result.get("configured_gamepads")
            if isinstance(chosen, list) and chosen:
                item = chosen[0]
                self.detected_gamepad = str(item["model"])
                self.gamepad_filter.set_text(
                    f"Modelo: {item['model']}\nID: {item['vendor_id']}:{item['product_id']}"
                )
            else:
                self.detected_gamepad = ""
                count = len(result.get("gamepads", []))
                self.gamepad_filter.set_text(
                    f"Filtro: {self.config.gamepad_name or 'qualquer controle'}"
                    + (f" · {count} outro(s) controle(s)" if count else "")
                )
            live_audio = result.get("tv_audio")
            configured_audio = result.get("configured_audio")
            if isinstance(live_audio, dict):
                audio_text = str(live_audio.get("description") or live_audio["name"])
                audio_tip = str(live_audio["name"])
            elif isinstance(configured_audio, dict):
                audio_text = str(configured_audio.get("description") or configured_audio["name"])
                audio_tip = str(configured_audio["name"])
            elif self.config.tv_sink:
                audio_text = "Aguardando áudio da TV ao ativá-la"
                audio_tip = self.config.tv_sink
            else:
                audio_text = "Detecção automática ao ativar a TV"
                audio_tip = None
            self.audio_target.set_text(audio_text)
            self.audio_target.set_tooltip_text(audio_tip)
            self.summary_audio.set_text(audio_text)
            self.summary_audio.set_tooltip_text(audio_tip)
            self.summary_audio_detail.set_text("Saída da TV" if live_audio else "Ao ativar a TV")
            self.update_target_preview()
            self.refresh()
            return False

        def populate_settings(self) -> None:
            self._populating_settings = True
            self.config = load()
            self._setting_mode = True
            for value, button in self.mode_buttons.items():
                button.set_active(value == self.config.mode)
            self._setting_mode = False
            self.connect_delay.set_value(self.config.connect_delay)
            self.disconnect_delay.set_value(self.config.disconnect_delay)
            self._setting_launchers = True
            self.steam.set_active(self.config.launcher_start == STEAM_START)
            self.custom_launcher_switch.set_active(self.config.custom_launcher_enabled)
            self.custom_close_switch.set_active(self.config.custom_launcher_close)
            self._setting_launchers = False
            self.custom_launcher_path.set_text(self.config.custom_launcher_path)
            self.custom_launcher_path.set_tooltip_text(self.config.custom_launcher_path or None)
            self.custom_launcher_args.set_text(shlex.join(self.config.custom_launcher_args))
            self.custom_launcher_switch.set_sensitive(bool(self.config.custom_launcher_path))
            self.custom_close_switch.set_sensitive(
                bool(self.config.custom_launcher_path)
                and Path(self.config.custom_launcher_path).suffix.casefold() != ".desktop")
            audio_name = self.config.tv_sink.rsplit(".", 1)[-1] if self.config.tv_sink else "Automático"
            self.audio_target.set_text(audio_name)
            self.audio_target.set_tooltip_text(self.config.tv_sink or None)
            self.summary_audio.set_text(audio_name)
            self.summary_audio.set_tooltip_text(self.config.tv_sink or None)
            self.summary_audio_detail.set_text("Ao ativar a TV")
            launcher_names = []
            if self.config.launcher_start:
                launcher_names.append("Steam Big Picture" if self.config.launcher_start == STEAM_START else
                                      "Comando personalizado")
            if self.config.custom_launcher_enabled:
                launcher_names.append(Path(self.config.custom_launcher_path).name)
            self.summary_launcher.set_text(" + ".join(launcher_names) or "Desativado")
            self.summary_launcher_detail.set_text("Configurado para a TV" if launcher_names else "Nenhum selecionado")
            self.summary_gamepad_detail.set_text(self.config.gamepad_name or "Qualquer controle")
            self.gamepad_filter.set_text("Filtro: " + (self.config.gamepad_name or "qualquer controle"))
            self.combo_value.set_text(" + ".join(self.config.activation_buttons) if self.config.activation_buttons
                                      else "Ao conectar o controle")
            self.target_display.set_text(self.config.tv_output)
            self.target_output_label.set_text(self.config.tv_output)
            self.audio_manual.set_text("")
            self.update_device_choices(self.last_scan, reset=True)
            if self.config.launcher_start and self.config.launcher_start != STEAM_START:
                self.steam.set_sensitive(False)
                self.steam.set_tooltip_text("Inicializador personalizado: edite o arquivo completo")
            else:
                self.steam.set_sensitive(True)
                self.steam.set_tooltip_text(None)
            self._populating_settings = False

        def queue_autosave(self, *_args: object, delay_ms: int = 550) -> None:
            if self._populating_settings or self._updating_devices:
                return
            if self._autosave_source:
                GLib.source_remove(self._autosave_source)
            self._autosave_source = GLib.timeout_add(delay_ms, self._autosave_settings)
            for label in self.save_feedback:
                label.set_text("Salvando alterações…")

        def _autosave_settings(self) -> bool:
            self._autosave_source = 0
            if self.busy:
                self._autosave_source = GLib.timeout_add(250, self._autosave_settings)
                return False
            self.save()
            return False

        def launcher_toggled(self, *_args: object) -> None:
            if not self._setting_launchers:
                self.queue_autosave(delay_ms=100)

        def mode_toggled(self, button: Gtk.ToggleButton, value: str) -> None:
            if getattr(self, "_setting_mode", False):
                return
            if button.get_active():
                self._setting_mode = True
                for other_value, other in self.mode_buttons.items():
                    if other_value != value:
                        other.set_active(False)
                self._setting_mode = False
            elif not any(other.get_active() for other in self.mode_buttons.values()):
                button.set_active(True)

        def hide_window(self, *_args: object) -> bool:
            self.window.hide()
            return True

        def show_window(self) -> None:
            self.window.show_all()
            self.window.present()

        def popup_menu(self, _icon: object, _button: int, _time: int) -> None:
            self.menu.popup_at_pointer(None)

        def refresh(self) -> bool:
            state = {}
            try:
                # The daemon processes commands sequentially. A status request
                # during activation competes with the operation it is waiting
                # for and can fill the socket backlog or freeze the GTK loop.
                state = (dict(self._last_service_state) if self.busy else
                         request("status", timeout=1))
                if not state.get("ok"):
                    raise RuntimeError(str(state.get("error", "serviço indisponível")))
                self._last_service_state = dict(state)
                self.online = True
                self.active = bool(state.get("active"))
                self.enabled = bool(state.get("enabled", True))
                awaiting_input = bool(state.get("awaiting_input"))
                awaiting_reconnect = bool(state.get("awaiting_reconnect"))
                controller = str(state.get("controller") or self.detected_gamepad or "Desconectado")
                self.status.set_text("TV ativa" if self.active else
                                     "Controle detectado — pressione um botão para ativar a TV" if awaiting_input else
                                     "Reconecte o controle para ativar a TV" if awaiting_reconnect else
                                     "Monitor principal ativo" if self.enabled else
                                     "CouchPad desativado — controle livre para jogar no PC")
                self.controller.set_text(controller)
                self.summary_gamepad.set_text(controller)
                self.summary_gamepad_detail.set_text(
                    "Pressione um botão" if awaiting_input else
                    "Reconecte para ativar" if awaiting_reconnect else
                    self.config.gamepad_name or "Qualquer controle")
                screen = self.config.tv_output if self.active else self.config.desktop_output
                shown = self.detected_screen if self.active and self.detected_screen else screen
                self.summary_screen.set_text(shown)
                self.current_display.set_text(shown)
                self.current_map_caption.set_text("TV ativa" if self.active else "Monitor do PC")
                self.summary_screen_detail.set_text("TV" if self.active else "Monitor do PC")
                self.badge.set_text("TV ativa" if self.active else
                                    "Aguardando botão" if awaiting_input else
                                    "Reconecte o controle" if awaiting_reconnect else
                                    "Monitor ativo" if self.enabled else "Desativado")
                if self.enabled:
                    self.badge.get_style_context().remove_class("status-idle")
                else:
                    self.badge.get_style_context().add_class("status-idle")
                self.icon.set_tooltip_text("CouchPad — TV ativa" if self.active else
                                           "CouchPad — pressione um botão" if awaiting_input else
                                           "CouchPad — reconecte o controle" if awaiting_reconnect else
                                           "CouchPad — desktop" if self.enabled else
                                           "CouchPad — desativado")
            except (OSError, ValueError, RuntimeError) as exc:
                self.online = False
                self.active = False
                self.enabled = False
                self.status.set_text("Monitor automático parado")
                self.controller.set_text(self.detected_gamepad or "Desconectado")
                self.summary_gamepad.set_text(self.detected_gamepad or "Desconectado")
                self.summary_screen.set_text(self.config.desktop_output)
                self.current_display.set_text(self.config.desktop_output)
                self.current_map_caption.set_text("Monitor do PC")
                self.summary_screen_detail.set_text("Monitor do PC")
                self.badge.set_text("Monitor parado")
                self.badge.get_style_context().add_class("status-idle")
                self.icon.set_tooltip_text("CouchPad — serviço parado")
                LOG.debug("Estado indisponível: %s", exc)
            self.activate_button.set_sensitive(self.online and self.enabled and not self.active and not self.busy)
            self.restore_button.set_sensitive(self.online and self.active and not self.busy)
            self.service_button.set_label("Desativar CouchPad" if self.online and self.enabled else
                                          "Ativar CouchPad" if self.online else "Iniciar serviço")
            self.service_button.set_sensitive(not self.busy)
            self.automation_description.set_text(
                "Vídeo e áudio estão na TV." if self.active else
                "Pressione um botão para iniciar na TV." if state.get("awaiting_input") else
                "Reconecte o controle para iniciar na TV." if state.get("awaiting_reconnect") else
                "Automação ativa para a TV." if self.online and self.enabled else
                "Automação desativada · controle livre no PC." if self.online else
                "Serviço parado."
            )
            banner_style = self.automation_banner.get_style_context()
            button_style = self.service_button.get_style_context()
            for style, on_class, off_class in (
                (banner_style, "automation-on", "automation-off"),
                (button_style, "automation-disable", "automation-enable"),
            ):
                style.remove_class(on_class)
                style.remove_class(off_class)
                style.add_class(on_class if self.online and self.enabled else off_class)
            self.toggle_item.set_label(self.service_button.get_label())
            self.toggle_item.set_sensitive(not self.busy)
            self.menu_activate.set_sensitive(self.online and self.enabled and not self.active and not self.busy)
            self.menu_restore.set_sensitive(self.online and self.active and not self.busy)
            self.menu_cancel.set_sensitive(self.online and bool(state.get("countdown_pending")) and not self.busy)
            for chooser in (self.tv_chooser, self.gamepad_chooser, self.audio_chooser, self.audio_manual):
                chooser.set_sensitive(not self.active and not self.busy)
            self.steam.set_sensitive(not self.busy and self.config.launcher_start in ((), STEAM_START))
            self.custom_launcher_switch.set_sensitive(not self.busy and bool(self.custom_launcher_path.get_text()))
            self.custom_close_switch.set_sensitive(
                not self.busy and bool(self.custom_launcher_path.get_text())
                and Path(self.custom_launcher_path.get_text()).suffix.casefold() != ".desktop")
            self.choose_launcher.set_sensitive(not self.busy)
            self.custom_launcher_args.set_sensitive(not self.busy)
            for button in self.mode_buttons.values():
                button.set_sensitive(not self.busy)
            self.connect_delay.set_sensitive(not self.busy)
            self.disconnect_delay.set_sensitive(not self.busy)
            return True

        def run_async(self, work: Callable[[], str]) -> None:
            if self.busy:
                return
            self.busy = True
            self.refresh()

            def worker() -> None:
                try:
                    message = work()
                except Exception as exc:
                    message = f"Falha: {exc}"
                GLib.idle_add(self.finish, message)

            threading.Thread(target=worker, daemon=True).start()

        def finish(self, message: str) -> bool:
            self.busy = False
            self.message.set_text(message)
            if self.saving_preferences:
                for label in self.save_feedback:
                    label.set_text(message)
                self.saving_preferences = False
            if message.startswith("Preferências salvas"):
                self.populate_settings()
                self.scan_devices()
            self.refresh()
            return False

        def send(self, command: str) -> None:
            def work() -> str:
                response = request(command, timeout=45)
                if not response.get("ok"):
                    raise RuntimeError(str(response.get("error", "comando recusado")))
                return {"activate": "TV ativada", "restore": "Desktop restaurado",
                        "cancel": "Troca cancelada; pressione um botão para tentar novamente"}[command]
            self.run_async(work)

        def toggle_enabled(self, *_args: object) -> None:
            command = "disable" if self.online and self.enabled else "enable"
            online = self.online

            def work() -> str:
                if online:
                    response = request(command, timeout=45)
                    if not response.get("ok"):
                        raise RuntimeError(str(response.get("error", "falha ao alterar estado")))
                    return "CouchPad desativado; controle livre no monitor do PC" if command == "disable" else "CouchPad ativado; reconecte o controle para usar a TV"
                if os.environ.get("COUCHPAD_APPIMAGE"):
                    from .portable import ensure_monitor
                    ensure_monitor()
                    return "Monitor da beta iniciado"
                result = subprocess.run(["systemctl", "--user", "start", "shiftpad-linux.service"],
                                        capture_output=True, text=True, timeout=25, env=host_environment())
                if result.returncode:
                    raise RuntimeError(result.stderr.strip() or "systemctl falhou")
                return "Serviço iniciado"

            self.run_async(work)

        def save(self, *_args: object) -> None:
            if self.busy:
                return
            mode = next((value for value, button in self.mode_buttons.items() if button.get_active()), None)
            connect_delay = self.connect_delay.get_value()
            disconnect_delay = self.disconnect_delay.get_value()
            steam_enabled = (self.steam.get_active()
                             if self.config.launcher_start in ((), STEAM_START) else None)
            custom_launcher_path = self.custom_launcher_path.get_text()
            custom_launcher_enabled = self.custom_launcher_switch.get_active()
            custom_launcher_close = self.custom_close_switch.get_active()
            custom_launcher_args = self.custom_launcher_args.get_text()
            tv_output = self.tv_chooser.get_active_id()
            tv_choice = self.tv_choices.get(tv_output, {})
            gamepad_selection = self.gamepad_chooser.get_active_id()
            if gamepad_selection == "__any__":
                chosen_gamepad = {"model": "", "vendor_id": "", "product_id": "", "uniq": ""}
            elif gamepad_selection == "__configured__":
                chosen_gamepad = {
                    "model": self.config.gamepad_name,
                    "vendor_id": self.config.gamepad_vendor_id,
                    "product_id": self.config.gamepad_product_id,
                    "uniq": self.config.gamepad_uniq,
                }
            else:
                chosen_gamepad = self.gamepad_choices.get(gamepad_selection)
            audio_choice = self.audio_chooser.get_active_id()
            tv_sink = self.audio_manual.get_text().strip() or (
                "" if audio_choice == "__auto__" else audio_choice)
            if not tv_output or not chosen_gamepad or tv_sink is None:
                feedback = "Selecione TV, controle e saída de áudio antes de salvar"
                self.message.set_text(feedback)
                for label in self.save_feedback:
                    label.set_text(feedback)
                return
            tv_edid = (self.config.tv_edid_sha256 if tv_output == self.config.tv_output
                       else str(tv_choice.get("edid_sha256") or ""))
            hardware_changed = (
                tv_output != self.config.tv_output or tv_edid != self.config.tv_edid_sha256
                or tv_sink != self.config.tv_sink
                or str(chosen_gamepad["model"]) != self.config.gamepad_name
                or str(chosen_gamepad["vendor_id"]) != self.config.gamepad_vendor_id
                or str(chosen_gamepad["product_id"]) != self.config.gamepad_product_id
                or str(chosen_gamepad.get("uniq", "")) != self.config.gamepad_uniq
            )

            def work() -> str:
                if hardware_changed:
                    try:
                        status = request("status", timeout=2)
                    except OSError:
                        status = {}
                    if status.get("active"):
                        raise ValueError("restaure o monitor antes de trocar os dispositivos")
                if tv_output != self.config.tv_output:
                    if not tv_edid:
                        raise ValueError("a nova TV precisa estar conectada e fornecer EDID")
                    fresh = next((item for item in discovery.display_devices()
                                  if item["output"] == tv_output and item["connected"]), None)
                    if not fresh or fresh.get("edid_sha256") != tv_edid:
                        raise ValueError("a TV escolhida foi desconectada ou mudou; detecte novamente")
                try:
                    parsed_args = tuple(shlex.split(custom_launcher_args))
                except ValueError as exc:
                    raise ValueError(f"argumentos do inicializador inválidos: {exc}") from exc
                save_basic_settings(
                    mode, connect_delay, disconnect_delay, steam_enabled,
                    custom_launcher_path=custom_launcher_path,
                    custom_launcher_enabled=custom_launcher_enabled,
                    custom_launcher_close=custom_launcher_close,
                    custom_launcher_args=parsed_args,
                    tv_output=tv_output,
                    tv_edid_sha256=tv_edid,
                    tv_sink=tv_sink,
                    gamepad_name=str(chosen_gamepad["model"]),
                    gamepad_vendor_id=str(chosen_gamepad["vendor_id"]),
                    gamepad_product_id=str(chosen_gamepad["product_id"]),
                    gamepad_uniq=str(chosen_gamepad.get("uniq", "")),
                )
                try:
                    response = request("reload", timeout=3)
                    if not response.get("ok"):
                        raise RuntimeError(str(response.get("error", "falha ao recarregar")))
                    return "Preferências salvas e aplicadas"
                except OSError:
                    return "Preferências salvas; serão usadas ao iniciar o monitor"

            self.saving_preferences = True
            for label in self.save_feedback:
                label.set_text("Salvando alterações…")
            self.run_async(work)

        def choose_custom_launcher(self, *_args: object) -> None:
            chooser = Gtk.FileChooserNative.new(
                "Escolher inicializador", self.window, Gtk.FileChooserAction.OPEN,
                "Selecionar", "Cancelar",
            )
            current = self.custom_launcher_path.get_text()
            if current and Path(current).is_file():
                chooser.set_filename(current)
            if chooser.run() == Gtk.ResponseType.ACCEPT:
                selected = chooser.get_filename()
                if (selected and Path(selected).is_file() and
                        (Path(selected).suffix.casefold() == ".desktop" or os.access(selected, os.X_OK))):
                    self._setting_launchers = True
                    self.custom_launcher_path.set_text(selected)
                    self.custom_launcher_path.set_tooltip_text(selected)
                    self.custom_launcher_switch.set_sensitive(True)
                    is_desktop_entry = Path(selected).suffix.casefold() == ".desktop"
                    self.custom_close_switch.set_sensitive(not is_desktop_entry)
                    if is_desktop_entry:
                        self.custom_close_switch.set_active(False)
                    self.custom_launcher_switch.set_active(True)
                    self._setting_launchers = False
                    self.queue_autosave(delay_ms=100)
                else:
                    self.message.set_text("Escolha um executável, AppImage ou atalho .desktop")
            chooser.destroy()

        def open_config(self, *_args: object) -> None:
            try:
                subprocess.Popen(["xdg-open", str(config_path())], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, env=host_environment())
            except OSError as exc:
                self.message.set_text(f"Não foi possível abrir o arquivo: {exc}")

    app = Tray()
    for launcher_switch in (app.steam, app.custom_launcher_switch, app.custom_close_switch):
        launcher_switch.connect("notify::active", app.launcher_toggled)
    app.custom_launcher_args.connect("changed", app.queue_autosave)
    app.tv_chooser.connect("changed", app.queue_autosave)
    app.gamepad_chooser.connect("changed", app.queue_autosave)
    app.audio_chooser.connect("changed", app.queue_autosave)
    app.audio_manual.connect("changed", app.queue_autosave)
    for mode_button in app.mode_buttons.values():
        mode_button.connect("toggled", lambda button: app.queue_autosave() if button.get_active() else None)
    app.connect_delay.connect("value-changed", app.queue_autosave)
    app.disconnect_delay.connect("value-changed", app.queue_autosave)
    Gtk.main()
