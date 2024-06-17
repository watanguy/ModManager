import os
import shutil
import json
import glob
from PyQt5 import QtWidgets, QtCore, QtGui

PRESETS_FILE = 'mod_presets.json'

class MoveThread(QtCore.QThread):
    update_status = QtCore.pyqtSignal(str, str, object)

    def __init__(self, folder_name, action, main_folder, parent=None):
        super(MoveThread, self).__init__(parent)
        self.folder_name = folder_name
        self.action = action
        self.main_folder = main_folder

    def run(self):
        try:
            if self.action == 'Disable':
                source_folder = os.path.join(self.main_folder, self.folder_name)
                target_folder = os.path.join(os.path.dirname(self.main_folder), 'disabledMods')
                if not os.path.exists(target_folder):
                    os.makedirs(target_folder)
                if os.path.exists(source_folder):
                    shutil.move(source_folder, target_folder)
                else:
                    raise FileNotFoundError(f'Source folder not found: {source_folder}')
            else:
                source_folder = os.path.join(os.path.dirname(self.main_folder), 'disabledMods', self.folder_name)
                target_folder = self.main_folder
                if os.path.exists(source_folder):
                    shutil.move(source_folder, target_folder)
                else:
                    raise FileNotFoundError(f'Source folder not found: {source_folder}')
            
            status = 'Success'
        except Exception as e:
            status = f'Error: {e}'
        
        self.update_status.emit(status, self.action, self.folder_name)

class ClickableDot(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()
    hovered = QtCore.pyqtSignal(bool)

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.default_color = color
        self.setStyleSheet(f"background-color: {color}; border-radius: 10px;")
        self.setFixedSize(20, 20)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    def enterEvent(self, event):
        self.setStyleSheet(f"background-color: {self.default_color}; border: 2px solid #fff; border-radius: 10px;")
        self.hovered.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(f"background-color: {self.default_color}; border-radius: 10px;")
        self.hovered.emit(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()

class FolderItem(QtWidgets.QWidget):
    def __init__(self, folder_name, action, manager, parent=None):
        super(FolderItem, self).__init__(parent)
        self.folder_name = folder_name
        self.action = action
        self.manager = manager
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

        color_map = {'Disable': '#77dd77', 'Enable': '#ff6961', 'Moving': '#fdfd96'}
        self.dot = ClickableDot(color_map[self.action])
        self.dot.clicked.connect(self.on_click)
        self.dot.hovered.connect(self.manager.on_hover_change)
        layout.addWidget(self.dot)

        self.label = QtWidgets.QLabel(self.folder_name)
        self.label.setStyleSheet("color: white;")
        layout.addWidget(self.label)

        layout.addStretch()

    def on_click(self):
        self.manager.toggle_folder(self.folder_name, self.action, self)

    def set_status(self, status):
        color_map = {'Disable': '#77dd77', 'Enable': '#ff6961', 'Moving': '#fdfd96'}
        self.dot.default_color = color_map[status]
        self.dot.setStyleSheet(f"background-color: {color_map[status]}; border-radius: 10px;")
        self.dot.setEnabled(status != 'Moving')

class ModManagerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.settings = QtCore.QSettings('ModManagerApp', 'ModManagerApp')
        self.main_folder = self.settings.value('main_folder', '')
        self.auto_refresh_state = self.settings.value('auto_refresh_state', False, type=bool)
        self.hovering = False
        self.filter_state = 'All'
        self.search_text = ''
        self.locked = False
        self.fixer_found = False

        self.initUI()
        self.auto_fill_mods_path()
        self.check_for_fixer()
        self.load_presets()

    def initUI(self):
        self.setWindowTitle('Mod Manager')
        self.setGeometry(100, 100, 800, 600)

        main_layout = QtWidgets.QVBoxLayout()

        path_layout = QtWidgets.QHBoxLayout()
        self.path_label = QtWidgets.QLabel('Main Folder Path:')
        self.path_label.setStyleSheet("color: white;")
        path_layout.addWidget(self.path_label)

        self.path_entry = QtWidgets.QLineEdit(self.main_folder)
        self.path_entry.textChanged.connect(self.validate_path)
        path_layout.addWidget(self.path_entry)

        self.lock_button = QtWidgets.QPushButton('Lock')
        self.lock_button.setCheckable(True)
        self.lock_button.toggled.connect(self.toggle_lock)
        path_layout.addWidget(self.lock_button)

        main_layout.addLayout(path_layout)

        search_layout = QtWidgets.QHBoxLayout()
        self.search_entry = QtWidgets.QLineEdit()
        self.search_entry.setPlaceholderText('Search Mods...')
        self.search_entry.textChanged.connect(self.update_search)
        search_layout.addWidget(self.search_entry)

        self.filter_all = QtWidgets.QRadioButton("All")
        self.filter_all.setStyleSheet("color: white;")
        self.filter_all.setChecked(True)
        self.filter_all.toggled.connect(self.update_filter)
        search_layout.addWidget(self.filter_all)

        self.filter_enabled = QtWidgets.QRadioButton("Enabled")
        self.filter_enabled.setStyleSheet("color: white;")
        self.filter_enabled.toggled.connect(self.update_filter)
        search_layout.addWidget(self.filter_enabled)

        self.filter_disabled = QtWidgets.QRadioButton("Disabled")
        self.filter_disabled.setStyleSheet("color: white;")
        self.filter_disabled.toggled.connect(self.update_filter)
        search_layout.addWidget(self.filter_disabled)

        main_layout.addLayout(search_layout)

        button_layout = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton('Refresh')
        self.refresh_button.clicked.connect(self.display_folders)
        button_layout.addWidget(self.refresh_button)

        self.auto_refresh_check = QtWidgets.QCheckBox('Auto Refresh')
        self.auto_refresh_check.setStyleSheet("color: white;")
        self.auto_refresh_check.setChecked(self.auto_refresh_state)
        self.auto_refresh_check.stateChanged.connect(self.toggle_auto_refresh)
        button_layout.addWidget(self.auto_refresh_check)

        self.run_fixer_button = QtWidgets.QPushButton('Run Fixer')
        self.run_fixer_button.clicked.connect(self.run_fixer)
        self.run_fixer_button.setVisible(False)
        button_layout.addWidget(self.run_fixer_button)

        main_layout.addLayout(button_layout)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(QtCore.Qt.AlignTop)  # Align items to the top
        self.scroll_area.setWidget(self.scroll_content)

        main_layout.addWidget(self.scroll_area)

        preset_layout = QtWidgets.QHBoxLayout()
        self.preset_entry = QtWidgets.QLineEdit()
        self.preset_entry.setPlaceholderText('Preset Name...')
        self.preset_entry.setFixedWidth(150)
        preset_layout.addWidget(self.preset_entry)

        self.save_preset_button = QtWidgets.QPushButton('Save Preset')
        self.save_preset_button.clicked.connect(self.save_preset)
        preset_layout.addWidget(self.save_preset_button)

        self.load_preset_button = QtWidgets.QPushButton('Load Preset')
        self.load_preset_button.clicked.connect(self.load_preset)
        preset_layout.addWidget(self.load_preset_button)

        self.delete_preset_button = QtWidgets.QPushButton('Delete Preset')
        self.delete_preset_button.clicked.connect(self.delete_preset)
        preset_layout.addWidget(self.delete_preset_button)

        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.setFixedWidth(200)
        preset_layout.addWidget(self.preset_combo)

        main_layout.addLayout(preset_layout)

        self.setLayout(main_layout)
        self.show()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.display_folders)

        if self.auto_refresh_state:
            self.timer.start(1000)

        self.validate_path()

    def auto_fill_mods_path(self):
        current_dir = os.getcwd()
        mods_path = os.path.join(current_dir, "Mods")
        if os.path.isfile(os.path.join(current_dir, "3DMigoto Loader.exe")) and os.path.isdir(mods_path):
            self.main_folder = mods_path
            self.path_entry.setText(mods_path)
            self.display_folders()

    def closeEvent(self, event):
        self.settings.setValue('main_folder', self.main_folder)
        self.settings.setValue('auto_refresh_state', self.auto_refresh_check.isChecked())
        event.accept()

    def validate_path(self):
        self.main_folder = self.path_entry.text()
        valid = len(self.main_folder) > 3 and '\\' in self.main_folder
        self.refresh_button.setEnabled(valid)
        self.auto_refresh_check.setEnabled(valid)
        self.check_for_fixer()
        self.load_presets()

    def toggle_auto_refresh(self):
        if self.auto_refresh_check.isChecked():
            self.timer.start(1000)
        else:
            self.timer.stop()

    def toggle_lock(self, checked):
        self.locked = checked
        self.path_entry.setReadOnly(self.locked)
        self.lock_button.setText('Unlock' if self.locked else 'Lock')

    def update_search(self, text):
        self.search_text = text
        self.display_folders()

    def update_filter(self):
        if self.filter_all.isChecked():
            self.filter_state = 'All'
        elif self.filter_enabled.isChecked():
            self.filter_state = 'Enabled'
        elif self.filter_disabled.isChecked():
            self.filter_state = 'Disabled'
        self.display_folders()

    def display_folders(self):
        if self.hovering:
            return

        self.main_folder = self.path_entry.text()
        if not os.path.isdir(self.main_folder):
            return

        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        subfolders = [f for f in os.listdir(self.main_folder) if os.path.isdir(os.path.join(self.main_folder, f))]
        disabled_folder = os.path.join(os.path.dirname(self.main_folder), 'disabledMods')
        if os.path.exists(disabled_folder):
            disabled_subfolders = [f for f in os.listdir(disabled_folder) if os.path.isdir(os.path.join(disabled_folder, f))]
        else:
            disabled_subfolders = []

        all_folders = [(f, 'Enable') for f in disabled_subfolders] + [(f, 'Disable') for f in subfolders]
        all_folders.sort(key=lambda x: x[0].lower())

        filtered_folders = []
        for folder, action in all_folders:
            if self.filter_state == 'All' or (self.filter_state == 'Enabled' and action == 'Disable') or (self.filter_state == 'Disabled' and action == 'Enable'):
                if self.search_text.lower() in folder.lower():
                    filtered_folders.append((folder, action))

        for folder, action in filtered_folders:
            item = FolderItem(folder, action, self)
            self.scroll_layout.addWidget(item)

    def toggle_folder(self, folder_name, action, item):
        item.set_status('Moving')
        self.move_thread = MoveThread(folder_name, action, self.main_folder)
        self.move_thread.update_status.connect(self.on_move_complete)
        self.move_thread.item = item
        self.move_thread.start()

    def on_move_complete(self, status, action, folder_name):
        if status == 'Success':
            # Remove success message box
            pass
        else:
            QtWidgets.QMessageBox.critical(self, 'Error', status)
        self.display_folders()

    def on_hover_change(self, is_hovering):
        self.hovering = is_hovering
        if not is_hovering and self.auto_refresh_check.isChecked():
            self.timer.start(1000)
        elif is_hovering:
            self.timer.stop()

    def save_preset(self):
        preset_name = self.preset_entry.text()
        if not preset_name:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'Preset name cannot be empty')
            return
        
        enabled_mods = [f for f in os.listdir(self.main_folder) if os.path.isdir(os.path.join(self.main_folder, f))]
        disabled_mods = []
        disabled_folder = os.path.join(os.path.dirname(self.main_folder), 'disabledMods')
        if os.path.exists(disabled_folder):
            disabled_mods = [f for f in os.listdir(disabled_folder) if os.path.isdir(os.path.join(disabled_folder, f))]

        preset_data = {
            'enabled': enabled_mods,
            'disabled': disabled_mods
        }

        try:
            with open(PRESETS_FILE, 'r') as file:
                presets = json.load(file)
        except FileNotFoundError:
            presets = {}

        if self.main_folder not in presets:
            presets[self.main_folder] = {}

        presets[self.main_folder][preset_name] = preset_data

        with open(PRESETS_FILE, 'w') as file:
            json.dump(presets, file, indent=4)

        self.preset_entry.clear()
        self.load_presets()
        QtWidgets.QMessageBox.information(self, 'Success', 'Preset saved successfully')

    def load_presets(self):
        self.preset_combo.clear()
        try:
            with open(PRESETS_FILE, 'r') as file:
                presets = json.load(file)
            directory_presets = presets.get(self.main_folder, {})
            self.preset_combo.addItems(directory_presets.keys())
        except FileNotFoundError:
            pass

    def load_preset(self):
        preset_name = self.preset_combo.currentText()
        if not preset_name:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'No preset selected')
            return

        try:
            with open(PRESETS_FILE, 'r') as file:
                presets = json.load(file)
        except FileNotFoundError:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'No presets found')
            return

        if self.main_folder not in presets or preset_name not in presets[self.main_folder]:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'Preset not found')
            return

        preset_data = presets[self.main_folder][preset_name]
        enabled_mods = preset_data['enabled']
        disabled_mods = preset_data['disabled']

        for mod in enabled_mods:
            source = os.path.join(os.path.dirname(self.main_folder), 'disabledMods', mod)
            destination = os.path.join(self.main_folder, mod)
            if os.path.exists(source):
                shutil.move(source, destination)

        for mod in disabled_mods:
            source = os.path.join(self.main_folder, mod)
            destination = os.path.join(os.path.dirname(self.main_folder), 'disabledMods', mod)
            if os.path.exists(source):
                shutil.move(source, destination)

        self.display_folders()
        QtWidgets.QMessageBox.information(self, 'Success', 'Preset loaded successfully')

    def delete_preset(self):
        preset_name = self.preset_combo.currentText()
        if not preset_name:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'No preset selected')
            return

        try:
            with open(PRESETS_FILE, 'r') as file:
                presets = json.load(file)
        except FileNotFoundError:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'No presets found')
            return

        if self.main_folder not in presets or preset_name not in presets[self.main_folder]:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'Preset not found')
            return

        del presets[self.main_folder][preset_name]

        with open(PRESETS_FILE, 'w') as file:
            json.dump(presets, file, indent=4)

        self.load_presets()
        QtWidgets.QMessageBox.information(self, 'Success', 'Preset deleted successfully')

    def check_for_fixer(self):
        # Check in the main folder
        fixer_files_main = glob.glob(os.path.join(self.main_folder, 'genshin_update_mods_*.exe'))

        # Check in the parent folder of the main folder
        parent_folder = os.path.dirname(self.main_folder)
        fixer_files_parent = glob.glob(os.path.join(parent_folder, 'genshin_update_mods_*.exe'))

        # Combine the results
        fixer_files = fixer_files_main + fixer_files_parent

        if fixer_files:
            self.fixer_found = True
            self.run_fixer_button.setVisible(True)
        else:
            self.fixer_found = False
            self.run_fixer_button.setVisible(False)


    def run_fixer(self):
        fixer_files = glob.glob(os.path.join(self.main_folder, 'genshin_update_mods_*.exe'))
        if fixer_files:
            os.startfile(fixer_files[0])

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    dark_palette = QtGui.QPalette()
    dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
    dark_palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    dark_palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
    app.setPalette(dark_palette)
    ex = ModManagerApp()
    sys.exit(app.exec_())
