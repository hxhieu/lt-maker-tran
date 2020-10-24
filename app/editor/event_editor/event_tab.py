from app.data.database import DB

from app.editor.base_database_gui import DatabaseTab
from app.editor.data_editor import SingleDatabaseEditor

from app.editor.event_editor import event_model, event_properties

class EventDatabase(DatabaseTab):
    @classmethod
    def create(cls, parent=None):
        data = DB.events
        title: str = "Event"
        right_frame = event_properties.EventProperties

        collection_model = event_model.EventModel
        dialog = cls(data, title, right_frame, None, collection_model, parent)
        return dialog

# Testing
# Run "python -m app.editor.event_editor.event_tab"
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    DB.load('default.ltproj')
    window = SingleDatabaseEditor(EventDatabase)
    window.show()
    app.exec_()
