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


DEFAULT_NUM_BUTTONS = 12
DEFAULT_NUM_AXES = 8


def default_config(num_buttons=DEFAULT_NUM_BUTTONS, num_axes=DEFAULT_NUM_AXES):
    return {
        "window": {"x": 120, "y": 120, "width": 980, "height": 720},
        "meta": {
            "num_buttons": int(num_buttons),
            "num_axes": int(num_axes),
        },
        "style": {
            "font_family": "Noto Sans CJK JP",
            "font_size": 12,
            "accent_color": "#3fd0ff",
            "button_idle": "#2b2f38",
            "button_pressed": "#3fd0ff",
            "panel_bg": "#1b1f26",
            "panel_2": "#232934",
            "text": "#edf2f7",
            "soft_text": "#aab4c0",
        },
        "layout": {
            "left_stick_axes": [0, 1],
            "right_stick_axes": [3, 4],
            "left_trigger_axis": 2,
            "right_trigger_axis": 5,
        },
        "labels": {
            "buttons": [f"B{i}" for i in range(num_buttons)],
            "axes": [f"A{i}" for i in range(num_axes)],
        },
    }


class ConfigManager:
    def __init__(self, num_buttons, num_axes):
        default_path = os.path.expanduser("~/.ros/virtual_joy_gui.yaml")
        self.path = rospy.get_param("~config_path", default_path)
        self.presets_dir = rospy.get_param("~presets_dir", os.path.expanduser("~/.ros/virtual_joy_presets"))
        self.config = default_config(num_buttons, num_axes)
        self.load()
        loaded_buttons = int(self.config.get("meta", {}).get("num_buttons", num_buttons))
        loaded_axes = int(self.config.get("meta", {}).get("num_axes", num_axes))
        self.apply_counts(loaded_buttons, loaded_axes)

    def deep_update(self, base, new):
        for k, v in new.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                self.deep_update(base[k], v)
            else:
                base[k] = v

    def apply_counts(self, num_buttons, num_axes):
        num_buttons = max(0, int(num_buttons))
        num_axes = max(0, int(num_axes))
        self.config.setdefault("meta", {})["num_buttons"] = num_buttons
        self.config.setdefault("meta", {})["num_axes"] = num_axes
        labels = self.config.setdefault("labels", {})
        btn_labels = labels.setdefault("buttons", [])
        axis_labels = labels.setdefault("axes", [])
        while len(btn_labels) < num_buttons:
            btn_labels.append(f"B{len(btn_labels)}")
        while len(axis_labels) < num_axes:
            axis_labels.append(f"A{len(axis_labels)}")
        del btn_labels[num_buttons:]
        del axis_labels[num_axes:]

    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            self.deep_update(self.config, loaded)
        except Exception as e:
            rospy.logwarn("Failed to load virtual joy config: %s", e)

    def save(self):
        dirpath = os.path.dirname(self.path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.config, f, allow_unicode=True, sort_keys=False)

    def list_presets(self):
        os.makedirs(self.presets_dir, exist_ok=True)
        names = []
        for fn in os.listdir(self.presets_dir):
            if fn.endswith(".yaml"):
                names.append(os.path.splitext(fn)[0])
        return sorted(names)

    def preset_path(self, name):
        safe = "".join(c for c in name if c.isalnum() or c in ("_", "-", " ")).strip()
        if not safe:
            safe = "preset"
        return os.path.join(self.presets_dir, safe + ".yaml")

    def save_preset(self, name, config):
        os.makedirs(self.presets_dir, exist_ok=True)
        with open(self.preset_path(name), "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    def load_preset(self, name):
        path = self.preset_path(name)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data


class StickWidget(QtWidgets.QWidget):
    valueChanged = QtCore.pyqtSignal(float, float)

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.x_val = 0.0
        self.y_val = 0.0
        self.dragging = False
        self.setMinimumSize(220, 220)

    def setValue(self, x, y):
        self.x_val = max(-1.0, min(1.0, float(x)))
        self.y_val = max(-1.0, min(1.0, float(y)))
        self.update()

    def reset(self):
        self.setValue(0.0, 0.0)
        self.valueChanged.emit(self.x_val, self.y_val)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self._update_from_pos(event.pos())

    def mouseMoveEvent(self, event):
        if self.dragging:
            self._update_from_pos(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False

    def mouseDoubleClickEvent(self, event):
        self.reset()

    def _update_from_pos(self, pos):
        side = min(self.width(), self.height()) - 30
        radius = side / 2.0
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        dx = (pos.x() - cx) / radius
        dy = (pos.y() - cy) / radius
        mag = math.hypot(dx, dy)
        if mag > 1.0:
            dx /= mag
            dy /= mag
        self.x_val = max(-1.0, min(1.0, dx))
        self.y_val = max(-1.0, min(1.0, -dy))
        self.valueChanged.emit(self.x_val, self.y_val)
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 30
        radius = side / 2.0
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        center = QtCore.QPointF(cx, cy)
        knob = QtCore.QPointF(cx + self.x_val * radius, cy - self.y_val * radius)

        p.fillRect(self.rect(), QtGui.QColor("#232934"))
        p.setPen(QtGui.QPen(QtGui.QColor("#d7dde5"), 2))
        p.setBrush(QtGui.QColor("#2b2f38"))
        p.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 16, 16)
        p.drawEllipse(center, radius, radius)
        p.drawLine(QtCore.QPointF(cx - radius, cy), QtCore.QPointF(cx + radius, cy))
        p.drawLine(QtCore.QPointF(cx, cy - radius), QtCore.QPointF(cx, cy + radius))
        p.drawEllipse(center, radius * 0.5, radius * 0.5)

        p.setPen(QtGui.QPen(QtGui.QColor("#3fd0ff"), 3))
        p.drawLine(center, knob)
        p.setBrush(QtGui.QColor("#3fd0ff"))
        p.drawEllipse(knob, 14, 14)

        p.setPen(QtGui.QColor("#edf2f7"))
        p.drawText(QtCore.QRectF(0, 8, self.width(), 22), QtCore.Qt.AlignCenter, self.title)
        p.drawText(
            QtCore.QRectF(0, self.height() - 28, self.width(), 20),
            QtCore.Qt.AlignCenter,
            f"x={self.x_val:+.2f}  y={self.y_val:+.2f}  |v|={min(1.0, math.hypot(self.x_val, self.y_val)):.2f}",
        )
        p.end()


class ButtonGrid(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal(int, int)

    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.labels = list(labels)
        self.buttons = []
        grid = QtWidgets.QGridLayout(self)
        grid.setSpacing(10)
        cols = 4
        for i, label in enumerate(self.labels):
            btn = QtWidgets.QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumSize(90, 54)
            btn.toggled.connect(lambda checked, idx=i: self.changed.emit(idx, 1 if checked else 0))
            self.buttons.append(btn)
            grid.addWidget(btn, i // cols, i % cols)

    def set_label(self, idx, text):
        if 0 <= idx < len(self.buttons):
            self.buttons[idx].setText(text)

    def values(self):
        return [1 if b.isChecked() else 0 for b in self.buttons]

    def reset(self):
        for b in self.buttons:
            b.setChecked(False)


class LabelEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent, config, num_buttons, num_axes):
        super().__init__(parent)
        self.config = config
        self.num_buttons = num_buttons
        self.num_axes = num_axes
        self.setWindowTitle("Label Editor")
        self.resize(560, 640)
        lay = QtWidgets.QVBoxLayout(self)
        tabs = QtWidgets.QTabWidget()
        lay.addWidget(tabs)

        btn_page = QtWidgets.QWidget()
        btn_form = QtWidgets.QFormLayout(btn_page)
        self.btn_edits = []
        for i in range(self.num_buttons):
            edit = QtWidgets.QLineEdit(self.config["labels"]["buttons"][i])
            btn_form.addRow(f"B{i}", edit)
            self.btn_edits.append(edit)
        tabs.addTab(btn_page, "Buttons")

        axis_page = QtWidgets.QWidget()
        axis_form = QtWidgets.QFormLayout(axis_page)
        self.axis_edits = []
        for i in range(self.num_axes):
            edit = QtWidgets.QLineEdit(self.config["labels"]["axes"][i])
            axis_form.addRow(f"A{i}", edit)
            self.axis_edits.append(edit)
        tabs.addTab(axis_page, "Axes")

        row = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("Save")
        close_btn = QtWidgets.QPushButton("Close")
        row.addWidget(save_btn)
        row.addWidget(close_btn)
        lay.addLayout(row)

        save_btn.clicked.connect(self.accept)
        close_btn.clicked.connect(self.reject)

    def apply_to_config(self):
        for i, e in enumerate(self.btn_edits):
            self.config["labels"]["buttons"][i] = e.text()
        for i, e in enumerate(self.axis_edits):
            self.config["labels"]["axes"][i] = e.text()


class LayoutEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent, config, num_buttons, num_axes):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Layout / Count Editor")
        self.resize(480, 340)
        lay = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        lay.addLayout(form)

        self.num_buttons_spin = QtWidgets.QSpinBox()
        self.num_buttons_spin.setRange(0, 128)
        self.num_buttons_spin.setValue(num_buttons)
        form.addRow("Button数", self.num_buttons_spin)

        self.num_axes_spin = QtWidgets.QSpinBox()
        self.num_axes_spin.setRange(0, 128)
        self.num_axes_spin.setValue(num_axes)
        form.addRow("Axis数", self.num_axes_spin)

        self.left_stick_x = QtWidgets.QSpinBox(); self.left_stick_x.setRange(0, 255)
        self.left_stick_y = QtWidgets.QSpinBox(); self.left_stick_y.setRange(0, 255)
        lst = QtWidgets.QHBoxLayout(); lst.addWidget(self.left_stick_x); lst.addWidget(self.left_stick_y)
        form.addRow("Left Stick axis", self._wrap(lst))

        self.right_stick_x = QtWidgets.QSpinBox(); self.right_stick_x.setRange(0, 255)
        self.right_stick_y = QtWidgets.QSpinBox(); self.right_stick_y.setRange(0, 255)
        rst = QtWidgets.QHBoxLayout(); rst.addWidget(self.right_stick_x); rst.addWidget(self.right_stick_y)
        form.addRow("Right Stick axis", self._wrap(rst))

        self.lt_axis = QtWidgets.QSpinBox(); self.lt_axis.setRange(0, 255)
        self.rt_axis = QtWidgets.QSpinBox(); self.rt_axis.setRange(0, 255)
        tr = QtWidgets.QHBoxLayout(); tr.addWidget(self.lt_axis); tr.addWidget(self.rt_axis)
        form.addRow("Trigger axis", self._wrap(tr))

        left = self.config.get("layout", {}).get("left_stick_axes", [0, 1])
        right = self.config.get("layout", {}).get("right_stick_axes", [3, 4])
        self.left_stick_x.setValue(int(left[0] if len(left) > 0 else 0))
        self.left_stick_y.setValue(int(left[1] if len(left) > 1 else 1))
        self.right_stick_x.setValue(int(right[0] if len(right) > 0 else 3))
        self.right_stick_y.setValue(int(right[1] if len(right) > 1 else 4))
        self.lt_axis.setValue(int(self.config.get("layout", {}).get("left_trigger_axis", 2)))
        self.rt_axis.setValue(int(self.config.get("layout", {}).get("right_trigger_axis", 5)))

        info = QtWidgets.QLabel("配列長の変更後はUIを再構築します。スティック・トリガの割り当てもここで変更できます。")
        info.setWordWrap(True)
        lay.addWidget(info)

        row = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("Apply")
        cancel_btn = QtWidgets.QPushButton("Cancel")
        row.addWidget(ok_btn)
        row.addWidget(cancel_btn)
        lay.addLayout(row)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def _wrap(self, layout):
        w = QtWidgets.QWidget()
        w.setLayout(layout)
        return w

    def result_data(self):
        return {
            "num_buttons": self.num_buttons_spin.value(),
            "num_axes": self.num_axes_spin.value(),
            "layout": {
                "left_stick_axes": [self.left_stick_x.value(), self.left_stick_y.value()],
                "right_stick_axes": [self.right_stick_x.value(), self.right_stick_y.value()],
                "left_trigger_axis": self.lt_axis.value(),
                "right_trigger_axis": self.rt_axis.value(),
            },
        }


class PresetSelectDialog(QtWidgets.QDialog):
    def __init__(self, parent, names):
        super().__init__(parent)
        self.setWindowTitle("Load Preset")
        self.resize(420, 320)
        lay = QtWidgets.QVBoxLayout(self)
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(names)
        lay.addWidget(self.list_widget)
        row = QtWidgets.QHBoxLayout()
        load_btn = QtWidgets.QPushButton("Load")
        close_btn = QtWidgets.QPushButton("Close")
        row.addWidget(load_btn)
        row.addWidget(close_btn)
        lay.addLayout(row)
        load_btn.clicked.connect(self.accept)
        close_btn.clicked.connect(self.reject)
        if names:
            self.list_widget.setCurrentRow(0)

    def selected_name(self):
        item = self.list_widget.currentItem()
        return item.text() if item else ""


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, cfg_mgr):
        super().__init__()
        self.cfg_mgr = cfg_mgr
        self.config = cfg_mgr.config
        self.num_buttons = int(self.config.get("meta", {}).get("num_buttons", rospy.get_param("~num_buttons", DEFAULT_NUM_BUTTONS)))
        self.num_axes = int(self.config.get("meta", {}).get("num_axes", rospy.get_param("~num_axes", DEFAULT_NUM_AXES)))
        self.publish_rate = float(rospy.get_param("~publish_rate", 30.0))
        self.joy_topic = rospy.get_param("~joy_topic", "/joy")
        self.pub = rospy.Publisher(self.joy_topic, Joy, queue_size=1)

        self.axes = [0.0] * self.num_axes
        self.buttons = [0] * self.num_buttons
        self.axis_value_labels = {}
        self.axis_name_labels = {}
        self.lt_slider = None
        self.rt_slider = None
        self.axis_sliders = []
        self.central = None
        self.left_stick = None
        self.right_stick = None
        self.button_grid = None
        self.reset_btn = None
        self.edit_btn = None
        self.layout_btn = None
        self.save_preset_btn = None
        self.load_preset_btn = None
        self.hold_center_check = None

        self.rebuild_ui()

        geom = self.config.get("window", {})
        self.setGeometry(geom.get("x", 120), geom.get("y", 120), geom.get("width", 980), geom.get("height", 720))

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.publish_joy)
        self.timer.start(max(1, int(1000.0 / self.publish_rate)))

    def rebuild_ui(self):
        self.cfg_mgr.apply_counts(self.num_buttons, self.num_axes)
        self.config = self.cfg_mgr.config
        self.axes = self._resize_list(self.axes, self.num_axes, 0.0)
        self.buttons = self._resize_list(self.buttons, self.num_buttons, 0)
        self.axis_value_labels = {}
        self.axis_name_labels = {}
        self.axis_sliders = []
        self._build_ui()
        self._apply_style()
        self.refresh_labels()
        self.reset_all()

    def _resize_list(self, arr, size, fill_value):
        out = list(arr[:size])
        while len(out) < size:
            out.append(fill_value)
        return out

    def _build_ui(self):
        self.setWindowTitle("Virtual Joy GUI")
        if self.central is not None:
            self.central.deleteLater()
        self.central = QtWidgets.QWidget()
        self.setCentralWidget(self.central)
        root = QtWidgets.QVBoxLayout(self.central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        top = QtWidgets.QHBoxLayout()
        self.topic_label = QtWidgets.QLabel(f"Publish: {self.joy_topic}")
        self.info_label = QtWidgets.QLabel(f"buttons={self.num_buttons}  axes={self.num_axes}  {self.publish_rate:.1f} Hz")
        top.addWidget(self.topic_label)
        top.addStretch(1)
        top.addWidget(self.info_label)
        root.addLayout(top)

        stick_row = QtWidgets.QHBoxLayout()
        self.left_stick = StickWidget("Left Stick")
        self.right_stick = StickWidget("Right Stick")
        stick_row.addWidget(self.left_stick, 1)
        stick_row.addWidget(self.right_stick, 1)
        root.addLayout(stick_row)

        lt_idx = int(self.config["layout"].get("left_trigger_axis", 2))
        rt_idx = int(self.config["layout"].get("right_trigger_axis", 5))
        self.lt_slider = self._make_axis_slider(lt_idx)
        self.rt_slider = self._make_axis_slider(rt_idx)
        trig_row = QtWidgets.QHBoxLayout()
        trig_row.addWidget(self._wrap_group("Left Trigger", self.lt_slider[0]))
        trig_row.addWidget(self._wrap_group("Right Trigger", self.rt_slider[0]))
        root.addLayout(trig_row)

        self.axis_sliders = []
        axis_box = QtWidgets.QGridLayout()
        skip_axes = set(self.config["layout"].get("left_stick_axes", [0, 1]) + self.config["layout"].get("right_stick_axes", [3, 4]))
        skip_axes.update([lt_idx, rt_idx])
        row = 0
        for i in range(self.num_axes):
            if i in skip_axes:
                continue
            widget, slider = self._make_axis_slider(i)
            self.axis_sliders.append((i, slider, widget))
            axis_box.addWidget(widget, row, 0)
            row += 1
        root.addWidget(self._wrap_group("Extra Axes", self._widget_from_layout(axis_box)))

        self.button_grid = ButtonGrid(self.config["labels"]["buttons"][:self.num_buttons])
        root.addWidget(self._wrap_group("Buttons", self.button_grid), 1)

        bottom = QtWidgets.QHBoxLayout()
        self.reset_btn = QtWidgets.QPushButton("Reset")
        self.edit_btn = QtWidgets.QPushButton("Label Edit")
        self.layout_btn = QtWidgets.QPushButton("Layout / Count")
        self.save_preset_btn = QtWidgets.QPushButton("Save Preset")
        self.load_preset_btn = QtWidgets.QPushButton("Load Preset")
        self.hold_center_check = QtWidgets.QCheckBox("Releaseでstickを中央へ戻す")
        self.hold_center_check.setChecked(True)
        bottom.addWidget(self.reset_btn)
        bottom.addWidget(self.edit_btn)
        bottom.addWidget(self.layout_btn)
        bottom.addWidget(self.save_preset_btn)
        bottom.addWidget(self.load_preset_btn)
        bottom.addWidget(self.hold_center_check)
        bottom.addStretch(1)
        root.addLayout(bottom)

        self.left_stick.valueChanged.connect(self.on_left_stick)
        self.right_stick.valueChanged.connect(self.on_right_stick)
        self.button_grid.changed.connect(self.on_button_changed)
        self.reset_btn.clicked.connect(self.reset_all)
        self.edit_btn.clicked.connect(self.open_label_editor)
        self.layout_btn.clicked.connect(self.open_layout_editor)
        self.save_preset_btn.clicked.connect(self.save_preset_dialog)
        self.load_preset_btn.clicked.connect(self.load_preset_dialog)

    def _widget_from_layout(self, layout):
        w = QtWidgets.QWidget()
        w.setLayout(layout)
        return w

    def _wrap_group(self, title, widget):
        box = QtWidgets.QGroupBox(title)
        lay = QtWidgets.QVBoxLayout(box)
        lay.addWidget(widget)
        return box

    def _make_axis_slider(self, idx):
        container = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel(self.axis_display_name(idx))
        value_label = QtWidgets.QLabel(self.axis_value_text(idx))
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(-1000, 1000)
        slider.setValue(int(round(self.get_axis_value(idx) * 1000.0)))
        slider.valueChanged.connect(lambda val, i=idx, lab=value_label: self.on_axis_slider(i, val, lab))
        lay.addWidget(label)
        lay.addWidget(slider, 1)
        lay.addWidget(value_label)
        self.axis_name_labels[idx] = label
        self.axis_value_labels[idx] = value_label
        return container, slider

    def axis_display_name(self, idx):
        if 0 <= idx < len(self.config["labels"]["axes"]):
            return f"{self.config['labels']['axes'][idx]} [{idx}]"
        return f"A{idx} [{idx}]"

    def axis_value_text(self, idx):
        return f"{self.get_axis_value(idx):+.2f}"

    def get_axis_value(self, idx):
        if 0 <= idx < len(self.axes):
            return float(self.axes[idx])
        return 0.0

    def _apply_style(self):
        s = self.config["style"]
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {s['panel_bg']};
                color: {s['text']};
                font-family: '{s['font_family']}';
                font-size: {s['font_size']}pt;
            }}
            QGroupBox {{
                border: 1px solid #4b5668;
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 10px;
                background: {s['panel_2']};
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }}
            QPushButton {{
                background: {s['button_idle']};
                border: 1px solid #5b6577;
                border-radius: 10px;
                padding: 8px;
            }}
            QPushButton:checked {{
                background: {s['button_pressed']};
                color: #07131a;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 1px solid {s['accent_color']};
            }}
            QSlider::groove:horizontal {{
                height: 10px;
                background: #2b2f38;
                border-radius: 5px;
            }}
            QSlider::handle:horizontal {{
                width: 20px;
                margin: -5px 0;
                border-radius: 10px;
                background: {s['accent_color']};
            }}
            QLineEdit, QSpinBox {{
                background: #161a20;
                border: 1px solid #4b5668;
                border-radius: 8px;
                padding: 6px;
            }}
            QListWidget {{
                background: #161a20;
                border: 1px solid #4b5668;
                border-radius: 8px;
            }}
        """)

    def refresh_labels(self):
        self.info_label.setText(f"buttons={self.num_buttons}  axes={self.num_axes}  {self.publish_rate:.1f} Hz")
        for idx, label in self.axis_name_labels.items():
            label.setText(self.axis_display_name(idx))
        if self.button_grid is not None:
            for i in range(min(self.num_buttons, len(self.config["labels"]["buttons"]))):
                self.button_grid.set_label(i, self.config["labels"]["buttons"][i])

    def on_left_stick(self, x, y):
        idxs = self.config["layout"].get("left_stick_axes", [0, 1])
        if len(idxs) >= 2:
            if 0 <= idxs[0] < self.num_axes:
                self.axes[idxs[0]] = x
                self.update_axis_value_label(idxs[0])
            if 0 <= idxs[1] < self.num_axes:
                self.axes[idxs[1]] = y
                self.update_axis_value_label(idxs[1])

    def on_right_stick(self, x, y):
        idxs = self.config["layout"].get("right_stick_axes", [3, 4])
        if len(idxs) >= 2:
            if 0 <= idxs[0] < self.num_axes:
                self.axes[idxs[0]] = x
                self.update_axis_value_label(idxs[0])
            if 0 <= idxs[1] < self.num_axes:
                self.axes[idxs[1]] = y
                self.update_axis_value_label(idxs[1])

    def on_axis_slider(self, idx, val, label):
        v = val / 1000.0
        if 0 <= idx < self.num_axes:
            self.axes[idx] = v
        label.setText(f"{v:+.2f}")

    def update_axis_value_label(self, idx):
        if idx in self.axis_value_labels:
            self.axis_value_labels[idx].setText(self.axis_value_text(idx))

    def on_button_changed(self, idx, value):
        if 0 <= idx < self.num_buttons:
            self.buttons[idx] = value

    def publish_joy(self):
        msg = Joy()
        msg.header.stamp = rospy.Time.now()
        msg.axes = list(self.axes)
        msg.buttons = list(self.buttons)
        self.pub.publish(msg)

    def reset_all(self):
        self.axes = [0.0] * self.num_axes
        self.buttons = [0] * self.num_buttons
        if self.left_stick is not None:
            self.left_stick.reset()
        if self.right_stick is not None:
            self.right_stick.reset()
        if self.button_grid is not None:
            self.button_grid.reset()
        if self.lt_slider is not None:
            self.lt_slider[1].setValue(0)
        if self.rt_slider is not None:
            self.rt_slider[1].setValue(0)
        for _, slider, _ in self.axis_sliders:
            slider.setValue(0)
        for idx in list(self.axis_value_labels.keys()):
            self.update_axis_value_label(idx)

    def open_label_editor(self):
        dialog = LabelEditorDialog(self, self.config, self.num_buttons, self.num_axes)
        if dialog.exec_():
            dialog.apply_to_config()
            self.refresh_labels()
            self.cfg_mgr.save()

    def open_layout_editor(self):
        dialog = LayoutEditorDialog(self, self.config, self.num_buttons, self.num_axes)
        if dialog.exec_():
            result = dialog.result_data()
            self.num_buttons = int(result["num_buttons"])
            self.num_axes = int(result["num_axes"])
            self.config["layout"] = result["layout"]
            self.cfg_mgr.apply_counts(self.num_buttons, self.num_axes)
            self.rebuild_ui()
            self.cfg_mgr.save()

    def current_config_snapshot(self):
        snap = copy.deepcopy(self.config)
        snap.setdefault("meta", {})["num_buttons"] = int(self.num_buttons)
        snap.setdefault("meta", {})["num_axes"] = int(self.num_axes)
        g = self.geometry()
        snap["window"] = {"x": g.x(), "y": g.y(), "width": g.width(), "height": g.height()}
        return snap

    def save_preset_dialog(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Save Preset", "Preset名")
        if not ok or not name.strip():
            return
        self.cfg_mgr.save_preset(name.strip(), self.current_config_snapshot())
        self.statusBar().showMessage(f"Preset saved: {name.strip()}", 3000)

    def load_preset_dialog(self):
        names = self.cfg_mgr.list_presets()
        if not names:
            QtWidgets.QMessageBox.information(self, "Load Preset", "保存済みプリセットがありません。")
            return
        dialog = PresetSelectDialog(self, names)
        if not dialog.exec_():
            return
        name = dialog.selected_name()
        if not name:
            return
        try:
            loaded = self.cfg_mgr.load_preset(name)
            self.cfg_mgr.config = default_config(self.num_buttons, self.num_axes)
            self.cfg_mgr.deep_update(self.cfg_mgr.config, loaded)
            self.config = self.cfg_mgr.config
            self.num_buttons = int(self.config.get("meta", {}).get("num_buttons", self.num_buttons))
            self.num_axes = int(self.config.get("meta", {}).get("num_axes", self.num_axes))
            self.cfg_mgr.apply_counts(self.num_buttons, self.num_axes)
            self.config = self.cfg_mgr.config
            self.rebuild_ui()
            geom = self.config.get("window", {})
            self.setGeometry(geom.get("x", 120), geom.get("y", 120), geom.get("width", 980), geom.get("height", 720))
            self.cfg_mgr.save()
            self.statusBar().showMessage(f"Preset loaded: {name}", 3000)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Load Preset", f"読み込みに失敗しました: {e}")

    def closeEvent(self, event):
        g = self.geometry()
        self.config["window"] = {"x": g.x(), "y": g.y(), "width": g.width(), "height": g.height()}
        self.config.setdefault("meta", {})["num_buttons"] = self.num_buttons
        self.config.setdefault("meta", {})["num_axes"] = self.num_axes
        self.cfg_mgr.save()
        super().closeEvent(event)


def main():
    rospy.init_node("virtual_joy_gui")
    num_buttons = int(rospy.get_param("~num_buttons", DEFAULT_NUM_BUTTONS))
    num_axes = int(rospy.get_param("~num_axes", DEFAULT_NUM_AXES))
    cfg_mgr = ConfigManager(num_buttons, num_axes)

    app = QtWidgets.QApplication(sys.argv)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    win = MainWindow(cfg_mgr)
    win.show()

    ros_timer = QtCore.QTimer()
    ros_timer.timeout.connect(lambda: None)
    ros_timer.start(50)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
