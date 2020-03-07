from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGridLayout, QPushButton, \
    QSizePolicy, QSplitter
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtCore import QAbstractItemModel, QAbstractListModel, QModelIndex

import copy

from app.data.data import Prefab
from app.extensions.custom_gui import RightClickListView

from app import utilities

class DatabaseTab(QWidget):
    def __init__(self, data, title, right_frame, deletion_criteria, collection_model, parent, 
                 button_text="Create %s", view_type=RightClickListView):
        QWidget.__init__(self, parent)
        self.window = parent
        self._data = data
        self.saved_data = self.save()
        self.title = title

        self.setWindowTitle('%s Editor' % self.title)
        self.setStyleSheet("font: 10pt;")

        self.left_frame = Collection(deletion_criteria, collection_model, self, button_text=button_text, view_type=view_type)
        self.right_frame = right_frame(self)
        self.left_frame.set_display(self.right_frame)

        self.splitter = QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.left_frame)
        self.splitter.addWidget(self.right_frame)
        self.splitter.setStyleSheet("QSplitter::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eee, stop:1 #ccc); border: 1px solid #777; width: 13px; margin-top: 2px; margin-bottom: 2px; border-radius: 4px;}")

        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)

        self.layout.addWidget(self.splitter)

    def update_list(self):
        self.left_frame.update_list()

    def tick(self):
        pass

    def reset(self):
        """
        Whenever the tab is changed, make sure to update the tab display
        Makes sure that current is what is being displayed
        """
        if self.right_frame.current:
            self.right_frame.set_current(self.right_frame.current)

    @classmethod
    def edit(cls, parent=None):
        dialog = cls.create(parent)
        dialog.exec_()

    def save(self):
        return self._data.save()

    def restore(self, data):
        self._data.restore(data)

    def apply(self):
        self.saved_data = self.save()

class Collection(QWidget):
    def __init__(self, deletion_criteria, collection_model, parent,
                 button_text="Create %s", view_type=RightClickListView):
        super().__init__(parent)
        self.window = parent
        self.database_editor = self.window.window

        self._data = self.window._data
        self.title = self.window.title
        
        self.display = None

        grid = QGridLayout()
        self.setLayout(grid)

        self.view = view_type(deletion_criteria, self)
        self.view.currentChanged = self.on_item_changed

        self.model = collection_model(self._data, self)
        self.view.setModel(self.model)

        self.view.setIconSize(QSize(32, 32))

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self.button = QPushButton(button_text % self.title)
        self.button.clicked.connect(self.model.append)

        grid.addWidget(self.view, 0, 0)
        grid.addWidget(self.button, 1, 0)

    def on_item_changed(self, curr, prev):
        if self._data:
            new_data = curr.internalPointer()  # Internal pointer is way too powerful
            if not new_data:
                new_data = self._data[curr.row()]
            if self.display:
                self.display.set_current(new_data)

    def set_display(self, disp):
        self.display = disp
        first_index = self.model.index(0)
        self.view.setCurrentIndex(first_index)

    def update_list(self):
        self.model.dataChanged.emit(self.model.index(0), self.model.index(self.model.rowCount()))                

class CollectionModel(QAbstractListModel):
    def __init__(self, data, window):
        super().__init__(window)
        self._data = data
        self.window = window

    def rowCount(self, parent=None):
        return len(self._data)

    def data(self, index, role):
        raise NotImplementedError

    def delete(self, idx):
        self._data.pop(idx)
        self.layoutChanged.emit()
        new_item = self._data[min(idx, len(self._data) - 1)]
        if self.window.display:
            self.window.display.set_current(new_item)

    def update(self):
        # self.dataChanged.emit(self.index(0), self.index(self.rowCount()))
        self.layoutChanged.emit()

    def create_new(self):
        raise NotImplementedError

    def append(self):
        self.create_new()
        view = self.window.view
        self.dataChanged.emit(self.index(0), self.index(self.rowCount()))
        last_index = self.index(self.rowCount() - 1)
        view.setCurrentIndex(last_index)
        self.update_watchers(self.rowCount() - 1)
        return last_index

    def new(self, idx):
        self.create_new()
        self._data.move_index(len(self._data) - 1, idx + 1)
        self.layoutChanged.emit()
        self.update_watchers(idx + 1)

    def duplicate(self, idx):
        obj = self._data[idx]
        new_nid = utilities.get_next_name(obj.nid, self._data.keys())
        if isinstance(obj, Prefab):
            serialized_obj = obj.serialize()
            print("Duplication!")
            print(serialized_obj, flush=True)
            new_obj = self._data.datatype.deserialize(serialized_obj)
        else:
            new_obj = copy.copy(obj)
        new_obj.nid = new_nid
        self._data.insert(idx + 1, new_obj)
        self.layoutChanged.emit()
        self.update_watchers(idx + 1)

    def update_watchers(self, idx):
        pass

class DragDropCollectionModel(CollectionModel):
    drop_to = None

    def supportedDropActions(self):
        return Qt.MoveAction

    def supportedDragActions(self):
        return Qt.MoveAction

    def insertRows(self, row, count, parent):
        if count < 1 or row < 0 or row > self.rowCount() or parent.isValid():
            return False
        # self.beginInsertRows(QModelIndex(), row, row + count - 1)
        self.drop_to = row
        self.layoutChanged.emit()
        # self.endInsertRows()
        # print("insertRows", row, count, flush=True)
        return True

    def do_drag_drop(self, index):
        if self.drop_to is None:
            return False
        if index < self.drop_to:
            self._data.move_index(index, self.drop_to - 1)
            return index, self.drop_to - 1
        else:
            self._data.move_index(index, self.drop_to)
            return index, self.drop_to

    def removeRows(self, row, count, parent):
        if count < 1 or row < 0 or (row + count) > self.rowCount() or parent.isValid():
            return False
        # self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        result = self.do_drag_drop(row)
        self.layoutChanged.emit()
        if result:
            self.update_drag_watchers(result[0], result[1])
        # self.endRemoveRows()
        # print("removeRows", row, count, flush=True)
        return True

    def update_drag_watchers(self, fro, to):
        pass

    def flags(self, index):
        if not index.isValid() or index.row() >= len(self._data) or index.model() is not self:
            return Qt.ItemIsDropEnabled
        else:
            return Qt.ItemIsDragEnabled | super().flags(index)

class MultiAttrCollectionModel(QAbstractItemModel):
    def __init__(self, data, headers, parent=None):
        super().__init__(parent)
        self.window = parent
        self._data = data
        self._headers = headers

        self.edit_locked = set()
        self.checked_columns = set()

    def index(self, row, column, parent_index=QModelIndex()):
        if self.hasIndex(row, column, parent_index):
            return self.createIndex(row, column)
        return QModelIndex()

    def parent(self, index):
        return QModelIndex()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def headerData(self, idx, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Vertical:
            return None
        elif orientation == Qt.Horizontal:
            return self._headers[idx].replace('_', ' ').capitalize()

    def data(self, index, role):
        if not index.isValid():
            return None
        if index.column() in self.checked_columns:
            if role == Qt.CheckStateRole:
                data = self._data[index.row()]
                attr = self._headers[index.column()]
                val = getattr(data, attr)
                return Qt.Checked if bool(val) else Qt.Unchecked
            else:
                return None
        elif role == Qt.DisplayRole or role == Qt.EditRole:
            data = self._data[index.row()]
            attr = self._headers[index.column()]
            return getattr(data, attr)
        return None

    def setData(self, index, value, role):
        # Would probably need to be overwritten by subclases
        if not index.isValid():
            return False
        data = self._data[index.row()]
        attr = self._headers[index.column()]
        current_value = getattr(data, attr)
        setattr(data, attr, value)
        self.change_watchers(data, attr, current_value, value)
        self.dataChanged.emit(index, index)
        return True

    def change_watchers(self, data, attr, old_value, new_value):
        pass

    def flags(self, index):
        basic_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemNeverHasChildren
        if getattr(self._data[index.row()], self._headers[0]) not in self.edit_locked or index.column() != 0:
            basic_flags |= Qt.ItemIsEditable
        if index.column() in self.checked_columns:
            basic_flags |= Qt.ItemIsUserCheckable
        return basic_flags

    def delete(self, idx):
        self._data.pop(idx)
        self.layoutChanged.emit()

    def update(self):
        self.dataChanged.emit(self.index(0), self.index(self.rowCount()))

    def create_new(self):
        raise NotImplementedError

    def append(self):
        self.create_new()
        view = self.window.view
        # self.dataChanged.emit(self.index(0), self.index(self.rowCount()))
        self.layoutChanged.emit()
        last_index = self.index(self.rowCount() - 1, 0)
        view.setCurrentIndex(last_index)
        self.update_watchers(self.rowCount() - 1)
        return last_index

    def new(self, idx):
        self.create_new()
        self._data.move_index(len(self._data) - 1, idx + 1)
        self.layoutChanged.emit()
        self.update_watchers(idx + 1)

    def duplicate(self, idx):
        obj = self._data[idx]
        new_nid = utilities.get_next_name(obj.nid, self._data.keys())
        if isinstance(obj, Prefab):
            serialized_obj = obj.serialize()
            print("Duplication!")
            print(serialized_obj, flush=True)
            new_obj = self._data.datatype.deserialize(serialized_obj)
        else:
            new_obj = copy.copy(obj)
        new_obj.nid = new_nid
        self._data.insert(idx + 1, new_obj)
        self.layoutChanged.emit()
        self.update_watchers(idx + 1)

    def update_watchers(self, idx):
        pass
