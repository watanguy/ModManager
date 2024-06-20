import os
import shutil
import json
import glob
import re
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
        self.keys_label = None
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

        self.keys_label = QtWidgets.QLabel('')
        self.keys_label.setStyleSheet("color: white;")
        self.keys_label.setVisible(False)
        layout.addWidget(self.keys_label)

        self.label.installEventFilter(self)
        self.label.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.label.customContextMenuRequested.connect(self.show_context_menu)

        layout.addStretch()

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.Enter and source is self.label:
            self.show_keys()
        elif event.type() == QtCore.QEvent.Leave and source is self.label:
            self.hide_keys()
        elif event.type() == QtCore.QEvent.MouseButtonDblClick and source is self.label:
            self.start_rename()
        return super(FolderItem, self).eventFilter(source, event)

    def show_context_menu(self, position):
        menu = QtWidgets.QMenu()
        rename_action = menu.addAction("Rename")
        open_action = menu.addAction("Open in Explorer")
        mark_broken_action = menu.addAction("Mark as broken")
        action = menu.exec_(self.label.mapToGlobal(position))
        if action == rename_action:
            self.start_rename()
        elif action == open_action:
            self.open_in_explorer()
        elif action == mark_broken_action:
            self.manager.mark_as_broken(self.folder_name, self.action)



    def start_rename(self):
        dialog = RenameDialog(self.folder_name, self.manager)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_name = dialog.get_new_name()
            if new_name and new_name != self.folder_name:
                try:
                    if self.action == 'Disable':
                        source_folder = os.path.join(self.manager.main_folder, self.folder_name)
                        target_folder = os.path.join(self.manager.main_folder, new_name)
                    else:
                        source_folder = os.path.join(os.path.dirname(self.manager.main_folder), 'disabledMods', self.folder_name)
                        target_folder = os.path.join(os.path.dirname(self.manager.main_folder), 'disabledMods', new_name)
                    
                    os.rename(source_folder, target_folder)
                    self.manager.update_preset_names(self.folder_name, new_name)
                    self.folder_name = new_name
                    self.label.setText(new_name)
                    self.manager.display_folders()
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, 'Error', str(e))

    def open_in_explorer(self):
        folder_path = os.path.join(self.manager.main_folder, self.folder_name)
        os.startfile(folder_path)

    def show_keys(self):
        keys = self.manager.get_keys_for_mod(self.folder_name)
        if keys:
            self.keys_label.setText(f"   |   Key(s): {', '.join(keys)}")
        else:
            self.keys_label.setText("   |   No keys found")
        self.keys_label.setVisible(True)

    def hide_keys(self):
        self.keys_label.setVisible(False)

    def on_click(self):
        self.manager.toggle_folder(self.folder_name, self.action, self)

    def set_status(self, status):
        color_map = {'Disable': '#77dd77', 'Enable': '#ff6961', 'Moving': '#fdfd96'}
        self.dot.default_color = color_map[status]
        self.dot.setStyleSheet(f"background-color: {color_map[status]}; border-radius: 10px;")
        self.dot.setEnabled(status != 'Moving')

class RenameDialog(QtWidgets.QDialog):
    def __init__(self, old_name, parent=None):
        super().__init__(parent)
        self.old_name = old_name
        self.new_name = old_name

        self.setWindowTitle("Rename Mod")
        self.setModal(True)
        self.setFixedSize(300, 150)

        layout = QtWidgets.QVBoxLayout()

        self.old_name_label = QtWidgets.QLabel(f"Current Name: {self.old_name}")
        self.old_name_label.setStyleSheet("color: white;")
        layout.addWidget(self.old_name_label)

        self.new_name_edit = QtWidgets.QLineEdit(self.new_name)
        self.new_name_edit.setStyleSheet("color: white; background-color: #333;")
        layout.addWidget(self.new_name_edit)

        button_layout = QtWidgets.QHBoxLayout()

        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_new_name(self):
        return self.new_name_edit.text().strip()

    def accept(self):
        self.new_name = self.get_new_name()
        if self.new_name and self.new_name != self.old_name:
            super().accept()
        else:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'New name must be different and non-empty')


class ModManagerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.settings = QtCore.QSettings('ModManagerApp', 'ModManagerApp')
        self.main_folder = self.settings.value('main_folder', '')
        self.auto_refresh_state = self.settings.value('auto_refresh_state', False, type=bool)
        self.confirmation_shown = self.settings.value('confirmation_shown', False, type=bool)
        self.hovering = False
        self.filter_state = 'All'
        self.search_text = ''
        self.locked = False
        self.fixer_found = False
        self.sorting_option = 'Name'

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

        self.always_on_top_check = QtWidgets.QCheckBox('Always on Top')
        self.always_on_top_check.setStyleSheet("color: white;")
        self.always_on_top_check.stateChanged.connect(self.toggle_always_on_top)
        button_layout.addWidget(self.always_on_top_check)

        self.run_fixer_button = QtWidgets.QPushButton('Run Fixer')
        self.run_fixer_button.clicked.connect(self.run_fixer)
        self.run_fixer_button.setVisible(False)
        button_layout.addWidget(self.run_fixer_button)

        # Adding Open... button
        self.open_button = QtWidgets.QComboBox()
        self.open_button.addItem("Open...")
        self.open_button.addItem("Root")
        self.open_button.addItem("Mods")
        self.open_button.addItem("Disabled mods")
        self.open_button.addItem("Broken mods")
        self.open_button.setFixedWidth(80)
        self.open_button.activated.connect(self.open_directory)
        button_layout.addWidget(self.open_button)

        self.sorting_combo = QtWidgets.QComboBox()
        self.sorting_combo.addItems(['Name', 'Date Added'])
        self.sorting_combo.currentTextChanged.connect(self.change_sorting_option)
        button_layout.addWidget(self.sorting_combo)

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

        self.update_preset_button = QtWidgets.QPushButton('Update Preset')
        self.update_preset_button.clicked.connect(self.update_preset)
        preset_layout.addWidget(self.update_preset_button)

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

    def toggle_always_on_top(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
        self.show()

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

    def change_sorting_option(self, option):
        self.sorting_option = option
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

        broken_folder = os.path.join(os.path.dirname(self.main_folder), 'brokenMods')
        broken_subfolders = []
        if os.path.exists(broken_folder):
            broken_subfolders = [f for f in os.listdir(broken_folder) if os.path.isdir(os.path.join(broken_folder, f))]

        all_folders = [(f, 'Enable') for f in disabled_subfolders if f not in broken_subfolders] + [(f, 'Disable') for f in subfolders if f not in broken_subfolders]
        if self.sorting_option == 'Name':
            all_folders.sort(key=lambda x: x[0].lower())
        elif self.sorting_option == 'Date Added':
            def get_ctime(folder_info):
                folder_name, action = folder_info
                if action == 'Disable':
                    return os.path.getctime(os.path.join(self.main_folder, folder_name))
                else:
                    return os.path.getctime(os.path.join(disabled_folder, folder_name))

            all_folders.sort(key=get_ctime)

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

    def get_keys_for_mod(self, mod_folder):
        merged_ini_path = os.path.join(self.main_folder, mod_folder, 'merged.ini')
        if not os.path.exists(merged_ini_path):
            return []

        keys = []
        with open(merged_ini_path, 'r') as file:
            for line in file:
                match = re.match(r'key\s*=\s*(.*)', line, re.IGNORECASE)
                if match:
                    keys.append(match.group(1).strip())
        return keys

    def update_preset_names(self, old_name, new_name):
        try:
            with open(PRESETS_FILE, 'r') as file:
                presets = json.load(file)
            for preset in presets.get(self.main_folder, {}).values():
                if old_name in preset['enabled']:
                    preset['enabled'].remove(old_name)
                    preset['enabled'].append(new_name)
                if old_name in preset['disabled']:
                    preset['disabled'].remove(old_name)
                    preset['disabled'].append(new_name)
            with open(PRESETS_FILE, 'w') as file:
                json.dump(presets, file, indent=4)
        except FileNotFoundError:
            pass

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

        missing_mods = []

        for mod in enabled_mods:
            source = os.path.join(os.path.dirname(self.main_folder), 'disabledMods', mod)
            destination = os.path.join(self.main_folder, mod)
            if os.path.exists(source):
                shutil.move(source, destination)
            else:
                missing_mods.append(mod)

        for mod in disabled_mods:
            source = os.path.join(self.main_folder, mod)
            destination = os.path.join(os.path.dirname(self.main_folder), 'disabledMods', mod)
            if os.path.exists(source):
                shutil.move(source, destination)
            else:
                missing_mods.append(mod)

        self.display_folders()

        if missing_mods:
            QtWidgets.QMessageBox.warning(self, 'Warning', f'The following mods were missing and could not be loaded: {", ".join(missing_mods)}')
        else:
            QtWidgets.QMessageBox.information(self, 'Success', 'Preset loaded successfully')


    def delete_preset(self):
        preset_name = self.preset_combo.currentText()
        if not preset_name:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'No preset selected')
            return

        reply = QtWidgets.QMessageBox.question(self, 'Confirmation', f'Are you sure you want to delete the preset "{preset_name}"?',
                                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.No:
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
        QtWidgets.QMessageBox.information(self, 'Success', f'Preset "{preset_name}" deleted successfully')


    def update_preset(self):
        preset_name = self.preset_combo.currentText()
        if not preset_name:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'No preset selected')
            return
        
        reply = QtWidgets.QMessageBox.question(self, 'Confirmation', f'Are you sure you want to update the preset "{preset_name}" with the current mod configuration?',
                                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.No:
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

        QtWidgets.QMessageBox.information(self, 'Success', f'Preset "{preset_name}" updated successfully')


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
        fixer_files_main = glob.glob(os.path.join(self.main_folder, 'genshin_update_mods_*.exe'))
        fixer_files_parent = glob.glob(os.path.join(os.path.dirname(self.main_folder), 'genshin_update_mods_*.exe'))
        fixer_files = fixer_files_main + fixer_files_parent
        if fixer_files:
            os.startfile(fixer_files[0])

    def mark_as_broken(self, folder_name, action):
        if not self.confirmation_shown:
            reply = QtWidgets.QMessageBox.question(
                self,
                'Confirmation',
                'Marking as broken will move the folder to a dedicated folder that is outside of the enabled and disabled mods and will no longer be shown in the mods view. Do you want to continue?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.No:
                return
            else:
                self.confirmation_shown = True
                self.settings.setValue('confirmation_shown', True)

        source_folder = os.path.join(self.main_folder, folder_name) if action == 'Disable' else os.path.join(os.path.dirname(self.main_folder), 'disabledMods', folder_name)
        target_folder = os.path.join(os.path.dirname(self.main_folder), 'brokenMods')
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        if os.path.exists(source_folder):
            try:
                shutil.move(source_folder, target_folder)
                QtWidgets.QMessageBox.information(self, 'Success', f'Mod "{folder_name}" marked as broken.')
                self.display_folders()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to mark as broken: {str(e)}')
        else:
            QtWidgets.QMessageBox.critical(self, 'Error', 'Source folder not found.')

    def open_directory(self, index):
        if index == 0:
            return  # "Open..." selected, do nothing

        if index == 1:
            directory = os.path.dirname(self.main_folder)  # Root
        elif index == 2:
            directory = self.main_folder  # Mods
        elif index == 3:
            directory = os.path.join(os.path.dirname(self.main_folder), 'disabledMods')  # Disabled mods
        elif index == 4:
            directory = os.path.join(os.path.dirname(self.main_folder), 'brokenMods')  # Broken mods

        if os.path.exists(directory):
            os.startfile(directory)
        else:
            QtWidgets.QMessageBox.warning(self, 'Warning', f'Directory not found: {directory}')

        # Reset the selection back to "Open..."
        QtCore.QTimer.singleShot(0, lambda: self.open_button.setCurrentIndex(0))


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
