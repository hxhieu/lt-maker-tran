import functools

from PyQt5.QtWidgets import QWidget, QButtonGroup, QInputDialog, QMenu, \
    QListWidgetItem, QRadioButton, QHBoxLayout, QLabel, QListWidget, QAction, \
    QColorDialog, QVBoxLayout
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor

from app.editor.icon_editor.icon_view import IconView
from app.utilities.data import Data
from app.resources import combat_anims
from app.editor.combat_animation_editor.palette_model import PaletteModel

from app.extensions.color_icon import ColorIcon
from app.extensions.custom_gui import RightClickListView

class AnimView(IconView):
    def get_color_at_pos(self, pixmap, pos):
        image = pixmap.toImage()
        current_color = image.pixel(*pos)
        color = QColor(current_color)
        return (color.red(), color.green(), color.blue())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        scene_pos = self.mapToScene(event.pos())
        pos = int(scene_pos.x()), int(scene_pos.y())

        # Need to get original frame with base palette
        frame_nid = self.window.frame_nid
        if not frame_nid:
            return
        weapon_anim = self.window.get_current_weapon_anim()
        frame = weapon_anim.frames.get(frame_nid)
        if not frame:
            return
        offset_x, offset_y = frame.offset
        pos = pos[0] - offset_x, pos[1] - offset_y
        pixmap = frame.pixmap

        if event.button() == Qt.LeftButton:
            base_color = self.get_color_at_pos(pixmap, pos)
            palette = self.window.get_current_palette()
            base_colors = combat_anims.base_palette.colors
            if base_color not in base_colors:
                print("Cannot find color: %s in %s" % (base_color, base_colors))
                return
            idx = base_colors.index(base_color)
            dlg = QColorDialog()
            c = palette.colors[idx]
            print(c, flush=True)
            dlg.setCurrentColor(QColor(*c))
            if dlg.exec_():
                new_color = QColor(dlg.currentColor())
                print(new_color, flush=True)
                color = new_color.getRgb()
                print(color, flush=True)
                palette_widget = self.window.palette_menu.get_palette_widget()
                icon = palette_widget.color_icons[idx]
                icon.change_color(new_color.name())

class PaletteDisplay(QWidget):
    def __init__(self, idx, palette, parent=None):
        super().__init__(parent)
        self.window = parent
        self.idx = idx
        self.palette = palette

        self.create_widgets()

    def create_widgets(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        radio_button = QRadioButton()
        self.window.radio_button_group.addButton(radio_button, self.idx)
        radio_button.clicked.connect(lambda: self.window.set_palette(self.idx))

        self.name_label = QLabel(self.palette.nid)

        self.palette_display = QHBoxLayout()
        self.palette_display.setSpacing(0)
        self.palette_display.setContentsMargins(0, 0, 0, 0)

        self.color_icons = []

        for idx, color in enumerate(self.palette.colors):
            qcolor = QColor(*color).name()
            icon = ColorIcon(qcolor, self)
            icon.set_size(16)
            icon.colorChanged.connect(functools.partial(self.on_color_change, idx))
            self.palette_display.addWidget(icon, 0, Qt.AlignCenter)
            self.color_icons.append(icon)

        layout.addWidget(radio_button)
        layout.addWidget(self.name_label)
        layout.addLayout(self.palette_display)

    def on_color_change(self, idx, color):
        color = color.getRgb()
        self.palette.colors[idx] = color[:3]

class PaletteDisplay(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent
        self.uniformItemSizes = True

        self.radio_button_group = QButtonGroup()
        self.palettes = []
        self.palette_widgets = []

        self.current_idx = 0

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.customMenuRequested)

    def customMenuRequested(self, pos):
        index = self.indexAt(pos)
        menu = QMenu(self)

        new_action = QAction("New", self, triggered=lambda: self.new(index))
        menu.addAction(new_action)
        if index.isValid():
            rename_action = QAction("Rename", self, triggered=lambda: self.rename(index))
            menu.addAction(rename_action)
            duplicate_action = QAction("Duplicate", self, triggered=lambda: self.duplicate(index))
            menu.addAction(duplicate_action)
            delete_action = QAction("Delete", self, triggered=lambda: self.delete(index))
            menu.addAction(delete_action)
            if len(self.palettes) <= 1:  # Can't delete when only one palette left
                delete_action.setEnabled(False)

        menu.popup(self.viewport().mapToGlobal(pos))

    def set_current(self, palettes):
        self.clear()

        for idx, palette in enumerate(palettes):
            self.palettes.append(palette)
            print(palette)

            item = QListWidgetItem(self)
            pf = PaletteWidget(idx, palette, self)
            self.palette_widgets.append(pf)
            item.setSizeHint(pf.minimumSizeHint())
            self.addItem(item)
            self.setItemWidget(item, pf)
            self.setMinimumWidth(self.sizeHintForColumn(0))

        if self.palettes:
            self.set_palette(0)

    def set_palette(self, idx):
        print("Set Palette: %s" % idx)
        self.current_idx = idx
        self.radio_button_group.button(idx).setChecked(True)

    def get_palette(self):
        return self.palettes[self.current_idx]

    def get_palette_widget(self):
        return self.palette_widgets[self.current_idx]

    def clear(self):
        # Clear out old radio buttons
        buttons = self.radio_button_group.buttons()
        for button in buttons[:]:
            self.radio_button_group.removeButton(button)
        self.palettes.clear()

        # for idx, l in reversed(list(enumerate(self.palette_widgets))):
        #     self.takeItem(idx)
        #     l.deleteLater()
        super().clear()
        self.palette_widgets.clear()
        self.current_idx = 0

    def new(self, index):
        palette_data = self.window.current.palettes
        new_nid = utilities.get_next_name("New", [p.nid for p in self.palettes])
        if palette_data:
            num_colors = len(palette_data[0].colors)
        else:
            num_colors = 16
        colors = combat_anims.base_palette.colors[:num_colors]
        new_palette = combat_anims.Palette(new_nid, colors)
        palette_data.insert(index.row() + 1, new_palette)

        self.set_current(palette_data)
        self.set_palette(self.current_idx)

    def duplicate(self, index):
        palette_data = self.window.current.palettes
        parent_palette = self.palettes[index.row()]
        new_nid = utilities.get_next_name(parent_palette.nid, [p.nid for p in self.palettes])
        colors = parent_palette.colors[:]
        new_palette = combat_anims.Palette(new_nid, colors)
        palette_data.insert(index.row() + 1, new_palette)

        self.set_current(palette_data)
        self.set_palette(self.current_idx)

    def delete(self, index):
        palette_data = self.window.current.palettes
        to_delete = self.palettes[index.row()]
        palette_data.delete(to_delete)

        self.set_current(palette_data)
        self.set_palette(self.current_idx)

    def rename(self, index):
        palette_data = self.window.current.palettes
        to_rename = self.palettes[index.row()]
        new_nid, ok = QInputDialog.getText(self, "Rename", "Enter New Name: ")
        if not new_nid or not ok:
            return

        new_nid = utilities.get_next_name(new_nid, palette_data.keys())
        palette_data.change_key(to_rename.nid, new_nid)
        palette_widget = self.palette_widgets[index.row()]
        palette_widget.name_label.setText(to_rename.nid)