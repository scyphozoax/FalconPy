from PyQt6.QtCore import QThread, pyqtSignal

class UpdateCheckThread(QThread):
    done = pyqtSignal(dict)

    def __init__(self, update_manager):
        super().__init__()
        self.update_manager = update_manager

    def run(self):
        try:
            info = self.update_manager.check_now()
            self.done.emit(info or {})
        except Exception:
            try:
                self.done.emit({"has_update": False, "latest_version": None, "download_url": None, "notes_url": None, "message": "error"})
            except Exception:
                pass