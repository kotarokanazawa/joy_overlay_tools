#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import math
import copy
import yaml
import signal
import rospy

from sensor_msgs.msg import Joy
from PyQt5 import QtCore, QtGui, QtWidgets

DEFAULT_STYLE = {
    "global_scale": 1.0,
    "font_family": "Noto Sans CJK JP",
    "font_size": 13,
    "line_width": 2,
    "background_alpha": 1,
    "colors": {
        "button_idle": "#2b2f38",
        "button_pressed": "#3fd0ff",
        "button_text": "#f2f5f7",
        "axis_idle": "#39414d",
        "axis_active": "#5df2c1",
        "axis_text": "#f2f5f7",
        "outline": "#d7dde5",
        "edit_grid": "#66ffffff",
        "panel_bg": "#dd14181f",
        "panel_border": "#99d0d7de",
        "selection": "#ffff66",
    },
}


def default_button_item(i, x, y):
    return {
        "type": "button",
        "index": i,
        "label": f"B{i}",
        "x": x,
        "y": y,
        "radius": 26,
        "visible": True,
        "idle_color": DEFAULT_STYLE["colors"]["button_idle"],
        "pressed_color": DEFAULT_STYLE["colors"]["button_pressed"],
        "text_color": DEFAULT_STYLE["colors"]["button_text"],
    }


def default_axis_item(i, x, y):
    return {
        "type": "axis_bar",
        "index": i,
        "label": f"A{i}",
        "x": x,
        "y": y,
        "width": 180,
        "height": 18,
        "orientation": "horizontal",
        "visible": True,
        "idle_color": DEFAULT_STYLE["colors"]["axis_idle"],
        "active_color": DEFAULT_STYLE["colors"]["axis_active"],
        "text_color": DEFAULT_STYLE["colors"]["axis_text"],
    }


def default_stick_item(name, x, y, axis_x, axis_y):
    return {
        "type": "stick",
        "name": name,
        "label": name,
        "axis_x": axis_x,
        "axis_y": axis_y,
        "x": x,
        "y": y,
        "radius": 56,
        "knob_radius": 16,
        "visible": True,
        "idle_color": DEFAULT_STYLE["colors"]["axis_idle"],
        "active_color": DEFAULT_STYLE["colors"]["axis_active"],
        "text_color": DEFAULT_STYLE["colors"]["axis_text"],
    }


def default_config():
    buttons = []
    for i in range(12):
        col = i % 4
        row = i // 4
        buttons.append(default_button_item(i, 820 + col * 80, 120 + row * 80))

    axes = []
    for i in range(8):
        axes.append(default_axis_item(i, 70, 420 + i * 34))

    sticks = [
        default_stick_item("L", 180, 180, 0, 1),
        default_stick_item("R", 420, 180, 3, 4),
    ]

    return {
        "window": {
            "x": 50,
            "y": 50,
            "width": 1200,
            "height": 900,
            "always_on_top": True,
            "click_through_when_not_editing": False,
        },
        "style": copy.deepcopy(DEFAULT_STYLE),
        "items": {
            "buttons": buttons,
            "axes": axes,
            "sticks": sticks,
        },
    }


class ConfigManager:
    def __init__(self):
        default_path = os.path.expanduser("~/.ros/joy_overlay_config.yaml")
        self.path = rospy.get_param("~config_path", default_path)
        self.config = default_config()
        self.load()

    def deep_update(self, base, new):
        for k, v in new.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                self.deep_update(base[k], v)
            else:
                base[k] = v

    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            self.deep_update(self.config, loaded)
        except Exception as e:
            rospy.logwarn("Failed to load config: %s", e)

    def save(self):
        dirpath = os.path.dirname(self.path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.config, f, allow_unicode=True, sort_keys=False)


class JoyState(QtCore.QObject):
    changed = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.axes = []
        self.buttons = []

    @QtCore.pyqtSlot(object)
    def update_from_msg(self, msg):
        self.axes = list(msg.axes)
        self.buttons = list(msg.buttons)
        self.changed.emit()


class RosJoyBridge(QtCore.QObject):
    joy_msg = QtCore.pyqtSignal(object)

    def __init__(self, topic_name):
        super().__init__()
        self.sub = rospy.Subscriber(topic_name, Joy, self.callback, queue_size=1)

    def callback(self, msg):
        self.joy_msg.emit(msg)


class ColorButton(QtWidgets.QPushButton):
    color_changed = QtCore.pyqtSignal(str)

    def __init__(self, color="#ffffff", parent=None):
        super().__init__(parent)
        self._color = color
        self.clicked.connect(self.pick_color)
        self.setFixedWidth(110)
        self.refresh()

    def color(self):
        return self._color

    def set_color(self, color, emit_signal=True):
        self._color = color
        self.refresh()
        if emit_signal:
            self.color_changed.emit(color)

    def refresh(self):
        c = QtGui.QColor(self._color)
        if not c.isValid():
            c = QtGui.QColor("#ffffff")
        rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, {c.alpha()})"
        self.setText(c.name(QtGui.QColor.HexArgb) if c.alpha() < 255 else c.name())
        text_color = "black" if c.lightness() > 140 else "white"
        self.setStyleSheet(
            "QPushButton {"
            f"background:{rgba};"
            f"color:{text_color};"
            "border:1px solid #999;"
            "padding:4px;"
            "}"
        )

    def pick_color(self):
        initial = QtGui.QColor(self._color)
        if not initial.isValid():
            initial = QtGui.QColor("#ffffff")
        c = QtWidgets.QColorDialog.getColor(initial, self, options=QtWidgets.QColorDialog.ShowAlphaChannel)
        if c.isValid():
            self.set_color(c.name(QtGui.QColor.HexArgb) if c.alpha() < 255 else c.name())


class ItemEditorPanel(QtWidgets.QWidget):
    item_changed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item = None
        self._updating = False
        self.form = QtWidgets.QFormLayout(self)
        self.form.setContentsMargins(8, 8, 8, 8)
        self.form.setSpacing(6)

        self.info = QtWidgets.QLabel("未選択")
        self.form.addRow("対象", self.info)

        self.label_edit = QtWidgets.QLineEdit()
        self.label_edit.textChanged.connect(self.apply)
        self.form.addRow("表示文字", self.label_edit)

        self.index_spin = QtWidgets.QSpinBox()
        self.index_spin.setRange(0, 255)
        self.index_spin.valueChanged.connect(self.apply)
        self.form.addRow("配列Index", self.index_spin)

        self.axis_x_spin = QtWidgets.QSpinBox()
        self.axis_x_spin.setRange(0, 255)
        self.axis_x_spin.valueChanged.connect(self.apply)
        self.form.addRow("axis_x", self.axis_x_spin)

        self.axis_y_spin = QtWidgets.QSpinBox()
        self.axis_y_spin.setRange(0, 255)
        self.axis_y_spin.valueChanged.connect(self.apply)
        self.form.addRow("axis_y", self.axis_y_spin)

        self.x_spin = QtWidgets.QDoubleSpinBox()
        self.x_spin.setRange(-5000, 5000)
        self.x_spin.setDecimals(1)
        self.x_spin.valueChanged.connect(self.apply)
        self.form.addRow("X", self.x_spin)

        self.y_spin = QtWidgets.QDoubleSpinBox()
        self.y_spin.setRange(-5000, 5000)
        self.y_spin.setDecimals(1)
        self.y_spin.valueChanged.connect(self.apply)
        self.form.addRow("Y", self.y_spin)

        self.radius_spin = QtWidgets.QDoubleSpinBox()
        self.radius_spin.setRange(1, 1000)
        self.radius_spin.setDecimals(1)
        self.radius_spin.valueChanged.connect(self.apply)
        self.form.addRow("半径", self.radius_spin)

        self.knob_radius_spin = QtWidgets.QDoubleSpinBox()
        self.knob_radius_spin.setRange(1, 1000)
        self.knob_radius_spin.setDecimals(1)
        self.knob_radius_spin.valueChanged.connect(self.apply)
        self.form.addRow("ノブ半径", self.knob_radius_spin)

        self.width_spin = QtWidgets.QDoubleSpinBox()
        self.width_spin.setRange(1, 5000)
        self.width_spin.setDecimals(1)
        self.width_spin.valueChanged.connect(self.apply)
        self.form.addRow("幅", self.width_spin)

        self.height_spin = QtWidgets.QDoubleSpinBox()
        self.height_spin.setRange(1, 5000)
        self.height_spin.setDecimals(1)
        self.height_spin.valueChanged.connect(self.apply)
        self.form.addRow("高さ", self.height_spin)

        self.orientation_combo = QtWidgets.QComboBox()
        self.orientation_combo.addItems(["horizontal", "vertical"])
        self.orientation_combo.currentTextChanged.connect(self.apply)
        self.form.addRow("Axis向き", self.orientation_combo)

        self.visible_check = QtWidgets.QCheckBox()
        self.visible_check.toggled.connect(self.apply)
        self.form.addRow("表示", self.visible_check)

        self.idle_color_btn = ColorButton()
        self.idle_color_btn.color_changed.connect(self.apply)
        self.form.addRow("通常色", self.idle_color_btn)

        self.active_color_btn = ColorButton()
        self.active_color_btn.color_changed.connect(self.apply)
        self.form.addRow("アクティブ色", self.active_color_btn)
        self._active_color_label = self.form.labelForField(self.active_color_btn)

        self.text_color_btn = ColorButton()
        self.text_color_btn.color_changed.connect(self.apply)
        self.form.addRow("文字色", self.text_color_btn)

    def set_row_visible(self, widget, visible):
        widget.setVisible(visible)
        label = self.form.labelForField(widget)
        if label is not None:
            label.setVisible(visible)

    def set_item(self, item):
        self._updating = True
        self.current_item = item
        enabled = item is not None
        for i in range(self.form.rowCount()):
            label_item = self.form.itemAt(i, QtWidgets.QFormLayout.LabelRole)
            field_item = self.form.itemAt(i, QtWidgets.QFormLayout.FieldRole)
            if label_item and label_item.widget():
                label_item.widget().setEnabled(enabled)
            if field_item and field_item.widget():
                field_item.widget().setEnabled(enabled)

        if item is None:
            self.info.setText("未選択")
            self._updating = False
            return

        self.info.setText(item.get("type", "?"))
        self.label_edit.blockSignals(True)
        self.index_spin.blockSignals(True)
        self.axis_x_spin.blockSignals(True)
        self.axis_y_spin.blockSignals(True)
        self.x_spin.blockSignals(True)
        self.y_spin.blockSignals(True)
        self.radius_spin.blockSignals(True)
        self.knob_radius_spin.blockSignals(True)
        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.orientation_combo.blockSignals(True)
        self.visible_check.blockSignals(True)

        self.label_edit.setText(item.get("label", ""))
        self.index_spin.setValue(int(item.get("index", 0)))
        self.axis_x_spin.setValue(int(item.get("axis_x", 0)))
        self.axis_y_spin.setValue(int(item.get("axis_y", 1)))
        self.x_spin.setValue(float(item.get("x", 0)))
        self.y_spin.setValue(float(item.get("y", 0)))
        self.radius_spin.setValue(float(item.get("radius", 20)))
        self.knob_radius_spin.setValue(float(item.get("knob_radius", 12)))
        self.width_spin.setValue(float(item.get("width", 120)))
        self.height_spin.setValue(float(item.get("height", 16)))
        self.orientation_combo.setCurrentText(str(item.get("orientation", "horizontal")))
        self.visible_check.setChecked(bool(item.get("visible", True)))
        self.idle_color_btn.set_color(item.get("idle_color", "#444444"), emit_signal=False)
        self.active_color_btn.set_color(
            item.get("pressed_color", item.get("active_color", "#00ffaa")),
            emit_signal=False,
        )
        self.text_color_btn.set_color(item.get("text_color", "#ffffff"), emit_signal=False)

        self.label_edit.blockSignals(False)
        self.index_spin.blockSignals(False)
        self.axis_x_spin.blockSignals(False)
        self.axis_y_spin.blockSignals(False)
        self.x_spin.blockSignals(False)
        self.y_spin.blockSignals(False)
        self.radius_spin.blockSignals(False)
        self.knob_radius_spin.blockSignals(False)
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
        self.orientation_combo.blockSignals(False)
        self.visible_check.blockSignals(False)

        t = item.get("type")
        self.set_row_visible(self.index_spin, t in ("button", "axis_bar"))
        self.set_row_visible(self.axis_x_spin, t == "stick")
        self.set_row_visible(self.axis_y_spin, t == "stick")
        self.set_row_visible(self.radius_spin, t in ("button", "stick"))
        self.set_row_visible(self.knob_radius_spin, t == "stick")
        self.set_row_visible(self.width_spin, t == "axis_bar")
        self.set_row_visible(self.height_spin, t == "axis_bar")
        self._updating = False

    def apply(self, *args):
        if self.current_item is None or self._updating:
            return
        item = self.current_item
        item["label"] = self.label_edit.text()
        item["x"] = self.x_spin.value()
        item["y"] = self.y_spin.value()
        item["visible"] = self.visible_check.isChecked()
        item["text_color"] = self.text_color_btn.color()
        t = item.get("type")
        if t == "button":
            item["index"] = self.index_spin.value()
            item["radius"] = self.radius_spin.value()
            item["idle_color"] = self.idle_color_btn.color()
            item["pressed_color"] = self.active_color_btn.color()
        elif t == "axis_bar":
            item["index"] = self.index_spin.value()
            item["width"] = self.width_spin.value()
            item["height"] = self.height_spin.value()
            item["orientation"] = self.orientation_combo.currentText()
            item["idle_color"] = self.idle_color_btn.color()
            item["active_color"] = self.active_color_btn.color()
        elif t == "stick":
            item["axis_x"] = self.axis_x_spin.value()
            item["axis_y"] = self.axis_y_spin.value()
            item["radius"] = self.radius_spin.value()
            item["knob_radius"] = self.knob_radius_spin.value()
            item["idle_color"] = self.idle_color_btn.color()
            item["active_color"] = self.active_color_btn.color()
        self.item_changed.emit()


class GlobalEditorPanel(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(8, 8, 8, 8)

        self.scale_spin = QtWidgets.QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 10.0)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setValue(self.config["style"].get("global_scale", 1.0))
        self.scale_spin.valueChanged.connect(self.on_change)
        form.addRow("全体倍率", self.scale_spin)

        self.font_spin = QtWidgets.QSpinBox()
        self.font_spin.setRange(6, 72)
        self.font_spin.setValue(self.config["style"].get("font_size", 13))
        self.font_spin.valueChanged.connect(self.on_change)
        form.addRow("文字サイズ", self.font_spin)

        self.line_spin = QtWidgets.QSpinBox()
        self.line_spin.setRange(1, 20)
        self.line_spin.setValue(self.config["style"].get("line_width", 2))
        self.line_spin.valueChanged.connect(self.on_change)
        form.addRow("線幅", self.line_spin)

        self.sel_btn = ColorButton(self.config["style"]["colors"].get("selection", "#ffff66"))
        self.sel_btn.color_changed.connect(self.on_change)
        form.addRow("選択色", self.sel_btn)

        self.grid_btn = ColorButton(self.config["style"]["colors"].get("edit_grid", "#66ffffff"))
        self.grid_btn.color_changed.connect(self.on_change)
        form.addRow("編集グリッド色", self.grid_btn)

    def on_change(self, *args):
        self.config["style"]["global_scale"] = self.scale_spin.value()
        self.config["style"]["font_size"] = self.font_spin.value()
        self.config["style"]["line_width"] = self.line_spin.value()
        self.config["style"]["colors"]["selection"] = self.sel_btn.color()
        self.config["style"]["colors"]["edit_grid"] = self.grid_btn.color()
        self.changed.emit()


class EditDialog(QtWidgets.QDialog):
    config_saved = QtCore.pyqtSignal()
    dialog_closed = QtCore.pyqtSignal()

    def __init__(self, overlay, cfg_mgr, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.cfg_mgr = cfg_mgr
        self._refreshing_list = False
        self.setWindowTitle("Joy Overlay Editor")
        self.resize(520, 760)
        self.setStyleSheet(
            "QDialog { background:#1b1f26; color:#e7edf3; }"
            "QWidget { color:#e7edf3; font-size:12px; }"
            "QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {"
            "background:#2b313d; border:1px solid #596273; padding:4px; }"
            "QPushButton { background:#2f3f55; border:1px solid #7a90aa; padding:6px; }"
            "QListWidget { background:#161a20; border:1px solid #495466; }"
            "QCheckBox::indicator { width:16px; height:16px; }"
        )

        root = QtWidgets.QVBoxLayout(self)

        self.mode_label = QtWidgets.QLabel("左ドラッグで移動 / 右クリックで編集")
        root.addWidget(self.mode_label)

        self.global_panel = GlobalEditorPanel(self.cfg_mgr.config)
        self.global_panel.changed.connect(self.overlay.on_global_style_changed)
        root.addWidget(self.global_panel)

        root.addWidget(QtWidgets.QLabel("描画要素"))
        self.list_widget = QtWidgets.QListWidget()
        root.addWidget(self.list_widget, 1)

        buttons = QtWidgets.QHBoxLayout()
        self.add_button_btn = QtWidgets.QPushButton("Button追加")
        self.add_axis_btn = QtWidgets.QPushButton("Axis追加")
        self.add_stick_btn = QtWidgets.QPushButton("Stick追加")
        self.delete_btn = QtWidgets.QPushButton("削除")
        buttons.addWidget(self.add_button_btn)
        buttons.addWidget(self.add_axis_btn)
        buttons.addWidget(self.add_stick_btn)
        buttons.addWidget(self.delete_btn)
        root.addLayout(buttons)

        self.item_panel = ItemEditorPanel()
        self.item_panel.item_changed.connect(self.overlay.request_repaint)
        root.addWidget(self.item_panel)

        action_row = QtWidgets.QHBoxLayout()
        self.reset_layout_btn = QtWidgets.QPushButton("描画リセット")
        self.save_btn = QtWidgets.QPushButton("保存")
        self.close_btn = QtWidgets.QPushButton("閉じる")
        action_row.addWidget(self.reset_layout_btn)
        action_row.addWidget(self.save_btn)
        action_row.addWidget(self.close_btn)
        root.addLayout(action_row)

        self.list_widget.currentRowChanged.connect(self.on_row_changed)
        self.add_button_btn.clicked.connect(self.add_button)
        self.add_axis_btn.clicked.connect(self.add_axis)
        self.add_stick_btn.clicked.connect(self.add_stick)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.reset_layout_btn.clicked.connect(self.reset_layout)
        self.save_btn.clicked.connect(self.save)
        self.close_btn.clicked.connect(self.close)

        self.refresh_list()

    def iter_all_items(self):
        all_items = []
        all_items.extend(self.cfg_mgr.config["items"]["buttons"])
        all_items.extend(self.cfg_mgr.config["items"]["axes"])
        all_items.extend(self.cfg_mgr.config["items"]["sticks"])
        return all_items

    def refresh_list(self):
        if self._refreshing_list:
            return
        self._refreshing_list = True
        try:
            selected_item = self.overlay.selected_item
            self.list_widget.blockSignals(True)
            self.list_widget.clear()
            for item in self.iter_all_items():
                if item.get("type") == "stick":
                    text = f"stick  {item.get('label','')}  ({item.get('axis_x',0)},{item.get('axis_y',1)})"
                else:
                    text = f"{item.get('type')}  {item.get('label','')}  idx={item.get('index',0)}"
                self.list_widget.addItem(text)
            self.list_widget.blockSignals(False)

            if selected_item is not None:
                all_items = self.iter_all_items()
                for i, item in enumerate(all_items):
                    if item is selected_item:
                        self.list_widget.blockSignals(True)
                        self.list_widget.setCurrentRow(i)
                        self.list_widget.blockSignals(False)
                        break
        finally:
            self._refreshing_list = False

    def on_row_changed(self, row):
        if self._refreshing_list:
            return
        items = self.iter_all_items()
        if 0 <= row < len(items):
            self.overlay.selected_item = items[row]
            self.item_panel.set_item(items[row])
        else:
            self.overlay.selected_item = None
            self.item_panel.set_item(None)
        self.overlay.request_repaint()

    def add_button(self):
        item = default_button_item(0, 800, 120)
        self.cfg_mgr.config["items"]["buttons"].append(item)
        self.overlay.selected_item = item
        self.refresh_list()
        self.item_panel.set_item(item)
        self.overlay.request_repaint()

    def add_axis(self):
        item = default_axis_item(0, 80, 420)
        self.cfg_mgr.config["items"]["axes"].append(item)
        self.overlay.selected_item = item
        self.refresh_list()
        self.item_panel.set_item(item)
        self.overlay.request_repaint()

    def add_stick(self):
        item = default_stick_item("N", 300, 300, 0, 1)
        self.cfg_mgr.config["items"]["sticks"].append(item)
        self.overlay.selected_item = item
        self.refresh_list()
        self.item_panel.set_item(item)
        self.overlay.request_repaint()

    def delete_selected(self):
        item = self.overlay.selected_item
        if item is None:
            return
        for key in ["buttons", "axes", "sticks"]:
            arr = self.cfg_mgr.config["items"][key]
            if item in arr:
                arr.remove(item)
                break
        self.overlay.selected_item = None
        self.refresh_list()
        self.item_panel.set_item(None)
        self.overlay.request_repaint()

    def reset_layout(self):
        new_cfg = default_config()
        self.cfg_mgr.config["items"] = copy.deepcopy(new_cfg["items"])
        self.overlay.config = self.cfg_mgr.config
        self.overlay.selected_item = None
        self.overlay.dynamic_expand_items()
        self.refresh_list()
        self.item_panel.set_item(None)
        self.overlay.request_repaint()

    def save(self):
        self.overlay.save_runtime_geometry_to_config()
        self.cfg_mgr.save()
        self.config_saved.emit()

    def closeEvent(self, event):
        self.dialog_closed.emit()
        super().closeEvent(event)


class OverlayWindow(QtWidgets.QWidget):
    def __init__(self, cfg_mgr, joy_state):
        super().__init__()
        self.cfg_mgr = cfg_mgr
        self.config = cfg_mgr.config
        self.joy_state = joy_state
        self.selected_item = None
        self.dragging_item = None
        self.drag_offset_logical = QtCore.QPointF(0.0, 0.0)
        self.dragging_window = False
        self.window_drag_offset = QtCore.QPoint(0, 0)
        self.edit_dialog = None
        self.edit_mode = False

        self.setWindowTitle("Joy Overlay")
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setMouseTracking(True)

        flags = QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool
        if self.config["window"].get("always_on_top", True):
            flags |= QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self.base_width = int(self.config["window"].get("width", 1200))
        self.base_height = int(self.config["window"].get("height", 900))
        x = int(self.config["window"].get("x", 50))
        y = int(self.config["window"].get("y", 50))
        self.apply_global_scale(initial_position=(x, y))

        self.joy_state.changed.connect(self.handle_joy_changed)
        self.dynamic_expand_items()

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update)
        timer.start(33)

    def get_scale(self):
        return float(self.config["style"].get("global_scale", 1.0))

    def logical_to_screen(self, point):
        s = self.get_scale()
        return QtCore.QPointF(point.x() * s, point.y() * s)

    def screen_to_logical(self, point):
        s = self.get_scale()
        if s <= 0.0:
            s = 1.0
        return QtCore.QPointF(point.x() / s, point.y() / s)

    def apply_global_scale(self, initial_position=None):
        s = self.get_scale()
        if s <= 0.0:
            s = 1.0
        new_w = max(1, int(round(self.base_width * s)))
        new_h = max(1, int(round(self.base_height * s)))
        if initial_position is not None:
            x, y = initial_position
        else:
            geom = self.geometry()
            x, y = geom.x(), geom.y()
        self.setGeometry(int(x), int(y), new_w, new_h)
        self.request_repaint()

    def on_global_style_changed(self):
        self.apply_global_scale()
        if self.edit_dialog is not None:
            self.edit_dialog.global_panel.scale_spin.blockSignals(True)
            self.edit_dialog.global_panel.scale_spin.setValue(self.get_scale())
            self.edit_dialog.global_panel.scale_spin.blockSignals(False)

    def save_runtime_geometry_to_config(self):
        geom = self.geometry()
        self.config["window"]["x"] = int(geom.x())
        self.config["window"]["y"] = int(geom.y())
        self.config["window"]["width"] = int(self.base_width)
        self.config["window"]["height"] = int(self.base_height)

    def request_repaint(self):
        self.update()
        if self.edit_dialog is not None:
            self.edit_dialog.refresh_list()

    def handle_joy_changed(self):
        self.dynamic_expand_items()
        self.update()

    def dynamic_expand_items(self):
        num_buttons = len(self.joy_state.buttons)
        num_axes = len(self.joy_state.axes)

        buttons = self.config["items"]["buttons"]
        axes = self.config["items"]["axes"]

        if len(buttons) < num_buttons:
            start = len(buttons)
            for i in range(start, num_buttons):
                col = i % 4
                row = i // 4
                buttons.append(default_button_item(i, 820 + col * 80, 120 + row * 80))

        if len(axes) < num_axes:
            start = len(axes)
            for i in range(start, num_axes):
                axes.append(default_axis_item(i, 70, 420 + i * 34))

    def open_editor(self):
        if self.edit_mode and self.edit_dialog is not None and self.edit_dialog.isVisible():
            self.edit_dialog.raise_()
            self.edit_dialog.activateWindow()
            return

        self.edit_mode = True
        self.setCursor(QtCore.Qt.OpenHandCursor)
        if self.edit_dialog is None:
            self.edit_dialog = EditDialog(self, self.cfg_mgr, self)
            self.edit_dialog.config_saved.connect(self.on_config_saved)
            self.edit_dialog.dialog_closed.connect(self.on_editor_dialog_closed)
        self.edit_dialog.refresh_list()
        if self.selected_item is not None:
            self.edit_dialog.item_panel.set_item(self.selected_item)
        self.edit_dialog.show()
        self.edit_dialog.raise_()
        self.edit_dialog.activateWindow()
        self.show()
        self.raise_()
        self.activateWindow()
        self.request_repaint()

    def on_config_saved(self):
        rospy.loginfo("Joy overlay config saved: %s", self.cfg_mgr.path)

    def close_editor(self, close_dialog=True):
        was_edit_mode = self.edit_mode
        self.edit_mode = False
        self.dragging_item = None
        self.dragging_window = False
        self.selected_item = None
        self.unsetCursor()
        if close_dialog and self.edit_dialog is not None and self.edit_dialog.isVisible():
            self.edit_dialog.blockSignals(True)
            self.edit_dialog.close()
            self.edit_dialog.blockSignals(False)
        self.show()
        self.raise_()
        self.activateWindow()
        if was_edit_mode:
            self.request_repaint()

    def on_editor_dialog_closed(self):
        if self.edit_mode:
            self.close_editor(close_dialog=False)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            if self.edit_mode and self.edit_dialog is not None and self.edit_dialog.isVisible():
                self.edit_dialog.raise_()
            else:
                self.open_editor()
            return

        if event.button() != QtCore.Qt.LeftButton:
            return

        logical_pos = self.screen_to_logical(event.localPos())
        item = self.hit_test(logical_pos) if self.edit_mode else None
        self.selected_item = item
        if self.edit_dialog is not None:
            self.edit_dialog.refresh_list()
            self.edit_dialog.item_panel.set_item(item)

        if self.edit_mode and item is not None:
            self.dragging_item = item
            self.drag_offset_logical = QtCore.QPointF(
                logical_pos.x() - float(item["x"]),
                logical_pos.y() - float(item["y"]),
            )
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        else:
            self.dragging_window = True
            self.window_drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self.setCursor(QtCore.Qt.SizeAllCursor)
        self.request_repaint()

    def mouseMoveEvent(self, event):
        if self.dragging_item is not None:
            logical_pos = self.screen_to_logical(event.localPos())
            self.dragging_item["x"] = round(logical_pos.x() - self.drag_offset_logical.x(), 1)
            self.dragging_item["y"] = round(logical_pos.y() - self.drag_offset_logical.y(), 1)
            if self.edit_dialog is not None:
                self.edit_dialog.item_panel.set_item(self.dragging_item)
                self.edit_dialog.refresh_list()
            self.request_repaint()
            return

        if self.dragging_window:
            self.move(event.globalPos() - self.window_drag_offset)
            self.request_repaint()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging_item = None
            self.dragging_window = False
            if self.edit_mode:
                self.setCursor(QtCore.Qt.OpenHandCursor)
            else:
                self.unsetCursor()

    def closeEvent(self, event):
        try:
            self.save_runtime_geometry_to_config()
            self.cfg_mgr.save()
        except Exception as e:
            rospy.logwarn("Close save failed: %s", e)
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            if self.edit_mode:
                self.close_editor()
                event.accept()
                return
            else:
                self.close()
                event.accept()
                return

    def hit_test(self, logical_pos):
        candidates = []
        candidates.extend(self.config["items"]["buttons"])
        candidates.extend(self.config["items"]["axes"])
        candidates.extend(self.config["items"]["sticks"])
        for item in reversed(candidates):
            if not item.get("visible", True):
                continue
            t = item.get("type")
            if t == "button":
                r = float(item.get("radius", 20))
                dx = logical_pos.x() - float(item["x"])
                dy = logical_pos.y() - float(item["y"])
                if dx * dx + dy * dy <= r * r:
                    return item
            elif t == "stick":
                r = float(item.get("radius", 56))
                dx = logical_pos.x() - float(item["x"])
                dy = logical_pos.y() - float(item["y"])
                if dx * dx + dy * dy <= r * r:
                    return item
            elif t == "axis_bar":
                w = float(item.get("width", 180))
                h = float(item.get("height", 18))
                rect = QtCore.QRectF(float(item["x"]), float(item["y"]), w, h + 24)
                if rect.contains(logical_pos):
                    return item
        return None

    def get_button_value(self, idx):
        if 0 <= idx < len(self.joy_state.buttons):
            return self.joy_state.buttons[idx]
        return 0

    def get_axis_value(self, idx):
        if 0 <= idx < len(self.joy_state.axes):
            return self.joy_state.axes[idx]
        return 0.0

    def qcolor(self, s, fallback="#ffffff"):
        c = QtGui.QColor(s if s else fallback)
        if not c.isValid():
            c = QtGui.QColor(fallback)
        return c

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setRenderHint(QtGui.QPainter.TextAntialiasing)

            scale = self.get_scale()
            font = QtGui.QFont(
                self.config["style"].get("font_family", "Sans"),
                max(1, int(self.config["style"].get("font_size", 13))),
            )
            painter.setFont(font)
            painter.scale(scale, scale)

            if self.edit_mode:
                self.draw_edit_overlay(painter)

            self.draw_sticks(painter)
            self.draw_axes(painter)
            self.draw_buttons(painter)
        finally:
            painter.end()

    def draw_edit_overlay(self, painter):
        grid_color = self.qcolor(self.config["style"]["colors"].get("edit_grid"), "#66ffffff")
        painter.setPen(QtGui.QPen(grid_color, 1, QtCore.Qt.DashLine))
        step = 40
        for x in range(0, self.base_width + 1, step):
            painter.drawLine(x, 0, x, self.base_height)
        for y in range(0, self.base_height + 1, step):
            painter.drawLine(0, y, self.base_width, y)

        panel_bg = self.qcolor(self.config["style"]["colors"].get("panel_bg"), "#aa000000")
        panel_bd = self.qcolor(self.config["style"]["colors"].get("panel_border"), "#88ffffff")
        message = "EDIT MODE\\n要素上の左ドラッグ: 要素移動\\n何もない場所の左ドラッグ: ウィンドウ移動\\n右クリック: 編集ウィンドウ\\nEsc: 終了"

        max_text_w = max(180, min(460, self.base_width - 48))
        text_rect = QtCore.QRectF(24, 22, max_text_w, 220)
        metrics = painter.fontMetrics()
        bounded = metrics.boundingRect(
            QtCore.QRect(int(text_rect.x()), int(text_rect.y()), int(text_rect.width()), int(text_rect.height())),
            int(QtCore.Qt.TextWordWrap | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop),
            message,
        )
        panel_rect = QtCore.QRectF(
            text_rect.x() - 12,
            text_rect.y() - 10,
            min(text_rect.width() + 24, self.base_width - 24),
            min(max(70, bounded.height() + 20), self.base_height - 24),
        )
        painter.setBrush(QtGui.QBrush(panel_bg))
        painter.setPen(QtGui.QPen(panel_bd, 1.5))
        painter.drawRoundedRect(panel_rect, 12, 12)
        painter.setPen(QtGui.QPen(QtGui.QColor("white"), 1))
        painter.drawText(
            panel_rect.adjusted(12, 10, -12, -10),
            int(QtCore.Qt.TextWordWrap | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop),
            message,
        )

    def draw_buttons(self, painter):
        outline = self.qcolor(self.config["style"]["colors"].get("outline"), "#ffffff")
        sel = self.qcolor(self.config["style"]["colors"].get("selection"), "#ffff66")
        lw = self.config["style"].get("line_width", 2)

        for item in self.config["items"]["buttons"]:
            if not item.get("visible", True):
                continue
            idx = int(item.get("index", 0))
            if idx >= len(self.joy_state.buttons):
                continue
            pressed = bool(self.get_button_value(idx))
            radius = float(item.get("radius", 26))
            center = QtCore.QPointF(float(item["x"]), float(item["y"]))
            fill = self.qcolor(item.get("pressed_color" if pressed else "idle_color"))
            painter.setBrush(QtGui.QBrush(fill))
            pen = QtGui.QPen(sel if item is self.selected_item else outline, lw + (1 if item is self.selected_item else 0))
            painter.setPen(pen)
            painter.drawEllipse(center, radius, radius)

            text_color = self.qcolor(item.get("text_color"), "#ffffff")
            painter.setPen(QtGui.QPen(text_color, 1))
            text_rect = QtCore.QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            painter.drawText(text_rect, QtCore.Qt.AlignCenter, item.get("label", f"B{idx}"))

            value_rect = QtCore.QRectF(center.x() - radius, center.y() + radius + 2, radius * 2, 18)
            painter.drawText(value_rect, QtCore.Qt.AlignCenter, f"[{idx}]")

    def draw_axes(self, painter):
        outline = self.qcolor(self.config["style"]["colors"].get("outline"), "#ffffff")
        sel = self.qcolor(self.config["style"]["colors"].get("selection"), "#ffff66")
        lw = self.config["style"].get("line_width", 2)

        for item in self.config["items"]["axes"]:
            if not item.get("visible", True):
                continue
            idx = int(item.get("index", 0))
            if idx >= len(self.joy_state.axes):
                continue
            val = max(-1.0, min(1.0, float(self.get_axis_value(idx))))
            w = float(item.get("width", 180))
            h = float(item.get("height", 18))
            x = float(item["x"])
            y = float(item["y"])
            orientation = str(item.get("orientation", "horizontal")).lower()

            painter.setPen(QtGui.QPen(sel if item is self.selected_item else outline, lw))
            painter.setBrush(QtGui.QBrush(self.qcolor(item.get("idle_color"), "#444444")))

            if orientation == "vertical":
                rect = QtCore.QRectF(x, y, h, w)
                painter.drawRoundedRect(rect, h / 2.0, h / 2.0)

                zero_y = y + w / 2.0
                fill_h = abs(val) * (w / 2.0)
                if val >= 0:
                    fill_rect = QtCore.QRectF(x, zero_y - fill_h, h, fill_h)
                else:
                    fill_rect = QtCore.QRectF(x, zero_y, h, fill_h)

                painter.setBrush(QtGui.QBrush(self.qcolor(item.get("active_color"), "#00ffaa")))
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRoundedRect(fill_rect, h / 2.0, h / 2.0)

                painter.setPen(QtGui.QPen(outline, 1))
                painter.drawLine(QtCore.QPointF(x - 4, zero_y), QtCore.QPointF(x + h + 4, zero_y))

                painter.setPen(QtGui.QPen(self.qcolor(item.get("text_color"), "#ffffff"), 1))
                painter.drawText(
                    QtCore.QRectF(x - 26, y - 22, max(90, h + 52), 18),
                    QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                    f"{item.get('label', f'A{idx}')} [{idx}]  {val:+.2f}",
                )
            else:
                rect = QtCore.QRectF(x, y, w, h)
                painter.drawRoundedRect(rect, h / 2.0, h / 2.0)

                zero_x = x + w / 2.0
                fill_w = abs(val) * (w / 2.0)
                if val >= 0:
                    fill_rect = QtCore.QRectF(zero_x, y, fill_w, h)
                else:
                    fill_rect = QtCore.QRectF(zero_x - fill_w, y, fill_w, h)

                painter.setBrush(QtGui.QBrush(self.qcolor(item.get("active_color"), "#00ffaa")))
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRoundedRect(fill_rect, h / 2.0, h / 2.0)

                painter.setPen(QtGui.QPen(outline, 1))
                painter.drawLine(QtCore.QPointF(zero_x, y - 4), QtCore.QPointF(zero_x, y + h + 4))

                painter.setPen(QtGui.QPen(self.qcolor(item.get("text_color"), "#ffffff"), 1))
                painter.drawText(
                    QtCore.QRectF(x, y - 22, w, 18),
                    QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                    f"{item.get('label', f'A{idx}')} [{idx}]  {val:+.2f}",
                )

    def draw_sticks(self, painter):
        outline = self.qcolor(self.config["style"]["colors"].get("outline"), "#ffffff")
        sel = self.qcolor(self.config["style"]["colors"].get("selection"), "#ffff66")
        lw = self.config["style"].get("line_width", 2)

        for item in self.config["items"]["sticks"]:
            if not item.get("visible", True):
                continue
            ax = int(item.get("axis_x", 0))
            ay = int(item.get("axis_y", 1))
            vx = max(-1.0, min(1.0, float(self.get_axis_value(ax))))
            vy_raw = max(-1.0, min(1.0, float(self.get_axis_value(ay))))
            vy = -vy_raw

            r = float(item.get("radius", 56))
            kr = float(item.get("knob_radius", 16))
            cx = float(item["x"])
            cy = float(item["y"])
            center = QtCore.QPointF(cx, cy)
            knob = QtCore.QPointF(cx + vx * r, cy + vy * r)
            mag = min(1.0, math.sqrt(vx * vx + vy_raw * vy_raw))

            painter.setBrush(QtGui.QBrush(self.qcolor(item.get("idle_color"), "#444444")))
            painter.setPen(QtGui.QPen(sel if item is self.selected_item else outline, lw))
            painter.drawEllipse(center, r, r)

            painter.setPen(QtGui.QPen(outline, 1))
            painter.drawLine(QtCore.QPointF(cx - r, cy), QtCore.QPointF(cx + r, cy))
            painter.drawLine(QtCore.QPointF(cx, cy - r), QtCore.QPointF(cx, cy + r))
            painter.drawEllipse(center, r * 0.5, r * 0.5)

            painter.setPen(QtGui.QPen(self.qcolor(item.get("active_color"), "#00ffaa"), max(2, lw)))
            painter.drawLine(center, knob)
            painter.setBrush(QtGui.QBrush(self.qcolor(item.get("active_color"), "#00ffaa")))
            painter.drawEllipse(knob, kr, kr)

            painter.setPen(QtGui.QPen(self.qcolor(item.get("text_color"), "#ffffff"), 1))
            text = f"{item.get('label', item.get('name', 'S'))} [{ax},{ay}]"
            painter.drawText(QtCore.QRectF(cx - r, cy - r - 28, 2 * r, 20), QtCore.Qt.AlignCenter, text)
            painter.drawText(
                QtCore.QRectF(cx - r - 20, cy + r + 4, 2 * r + 40, 20),
                QtCore.Qt.AlignCenter,
                f"x={vx:+.2f}  y={vy_raw:+.2f}  |v|={mag:.2f}",
            )


def main():
    rospy.init_node("joy_overlay_visualizer", disable_signals=True)
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    topic_name = rospy.get_param("~joy_topic", "/joy")

    cfg_mgr = ConfigManager()
    joy_state = JoyState()
    bridge = RosJoyBridge(topic_name)
    bridge.joy_msg.connect(joy_state.update_from_msg)

    win = OverlayWindow(cfg_mgr, joy_state)
    win.show()

    def handle_sigint(*_args):
        QtWidgets.QApplication.quit()

    signal.signal(signal.SIGINT, handle_sigint)
    sig_timer = QtCore.QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(100)

    exit_code = app.exec_()
    try:
        win.save_runtime_geometry_to_config()
        cfg_mgr.save()
    except Exception as e:
        rospy.logwarn("Final save failed: %s", e)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
