
import os
import sys
import cv2
import json
import shutil
import subprocess
from datetime import datetime

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *


class QCheckableFileSystemModel(QFileSystemModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paths_list = []

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.CheckStateRole and index.column() == 0:
            if self.fileName(index) in self.paths_list:
                return Qt.Checked
            else:
                return Qt.Unchecked
        else:
            return super().data(index, role)

    # Put only base name in the paths_list
    def updatePaths(self, paths_list):
        self.paths_list = paths_list
        self.layoutChanged.emit()


class QKeyTreeView(QTreeView):

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_6: # to skip
            down_arrow_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Down, Qt.NoModifier)
            super().keyPressEvent(down_arrow_event)
        elif event.key() == Qt.Key_4: # to skip
            up_arrow_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Up, Qt.NoModifier)
            super().keyPressEvent(up_arrow_event)
        else:
            super().keyPressEvent(event)


class FileTree(QWidget):

    tree_clicked = pyqtSignal()
    selection_changed = pyqtSignal()
    section_resized = pyqtSignal()

    name_filters = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.tiff", "*.tif", "*.svg",
                    "*.mp4", "*.avi", "*.mov", "*.wmv", "*.flv", "*.mpeg", "*.mpg", "*.mkv", "*.webm", "*.3gp", "*.m4v", "*.ogv", "*.vob", "*.ts", "*.pdf"]

    def __init__(self):
        super(FileTree, self).__init__()
        with open('logs/logs.json', 'r') as f:
            self.logs = json.load(f)
        self.initUI()

    def initUI(self):

        root_dir = self.logs['last_dir']

        ### File Tree Pane ###
        self.tree = QKeyTreeView()
        self.tree.setFrameShape(QFrame.StyledPanel)

        # Set file model
        self.file_model = QCheckableFileSystemModel()
        self.file_model.setRootPath(root_dir)
        self.file_model.setNameFilters(self.name_filters)
        self.file_model.setNameFilterDisables(False)
        self.file_model.setReadOnly(True)

        # Set model
        self.tree.setModel(self.file_model)
        self.tree.setSelectionMode(QTreeView.SingleSelection)
        self.tree.selectionModel().selectionChanged.connect(self.selection_changed.emit)
        self.tree.header().sectionResized.connect(self.section_resized)

        # Cosmetic options
        self.tree.setSortingEnabled(False)
        self.tree.setIndentation(10)
        self.tree.setIndentation(10)
        self.tree.hideColumn(1) # Hide size column
        self.tree.hideColumn(3) # Hide date modified column
        for w in range(len(self.logs['column_widths'])):
            self.tree.setColumnWidth(w, self.logs['column_widths'][w])

        # Settings
        root_index = self.file_model.index(root_dir)
        self.tree.setRootIndex(root_index)
        self.tree.setCurrentIndex(self.file_model.index(root_dir))
        
        self.tree.clicked.connect(self.tree_clicked.emit)

        ### Buttons ###
        self.button_changeDir = QPushButton('Change Dir')
        self.button_changeDir.clicked.connect(self.changeDir)
        
        self.show_all_files = False
        self.button_showAll = QPushButton('Show All')
        self.button_showAll.clicked.connect(self.showAll)

        self.button_goParent = QPushButton('🠙')
        self.button_goParent.setFixedWidth(20)
        self.button_goParent.clicked.connect(self.goParent)

        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.addWidget(self.button_changeDir)
        self.button_layout.addWidget(self.button_showAll)
        self.button_layout.addWidget(self.button_goParent)
        
        ## Layout ##
        self.tree_layout = QVBoxLayout(self)
        self.tree_layout.setContentsMargins(0, 0, 0, 0)
        self.tree_layout.addWidget(self.tree)
        self.tree_layout.addLayout(self.button_layout)

    def changeDir(self):
        dir = QFileDialog.getExistingDirectory(self, 'Select Directory')
        if dir:
            self.file_model.setRootPath(dir)
            self.tree.setRootIndex(self.file_model.index(dir))
            self.tree.setCurrentIndex(self.file_model.index(dir))

    def showAll(self):
        self.show_all_files = not self.show_all_files
        if self.show_all_files:
            self.file_model.setNameFilterDisables(True)
            self.button_showAll.setText("Only Show Media")
        else:
            self.file_model.setNameFilterDisables(False)
            self.button_showAll.setText("Show All Files")

    def goParent(self):
        parent_path = os.path.dirname(self.file_model.rootPath())
        print(self.file_model.rootPath())
        print(parent_path)
        if parent_path:
            self.file_model.setRootPath(parent_path)
            self.tree.setRootIndex(self.file_model.index(parent_path))


class MediaDisplay(QWidget):

    def __init__(self):
        super(MediaDisplay, self).__init__()
        self.volume_init = 100
        self.last_volume = self.volume_init
        self.initUI()

    def initUI(self):

        ## Set label for images ##
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")

        self.image_desc = QLineEdit(self)
        self.image_desc.setReadOnly(True)
        self.image_desc.setFixedHeight(25)
        self.image_desc.setText("")

        self.image_layout = QVBoxLayout(self)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.addWidget(self.image_label)
        self.image_layout.addWidget(self.image_desc)

        self.image_widget = QWidget(self)
        self.image_widget.setLayout(self.image_layout)

        ## Set player for videos ##
        self.media_player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setNotifyInterval(10)
        self.video_widget.mousePressEvent = self.onVideoClicked

        # Set play/pause button, initially set to play
        self.play_button = QPushButton(self)
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.play_button.clicked.connect(self.playClicked)

        # Set speed button, initially set to 1x
        self.speed_button = QPushButton(self)
        self.speed_button.setText("1x")
        self.speed_button.setFixedWidth(30)
        self.speed_button.clicked.connect(self.speedClicked)
        self.media_player.setPlaybackRate(1.0)

        # Set time label
        self.time_label = QLabel(self)
        self.time_label.setText("--:--/--:--")
        
        # Set time slider
        self.time_slider = QSlider(Qt.Horizontal, self)
        self.time_slider.setRange(0, 1)
        self.time_slider.sliderMoved.connect(self.setPlayerPos)
        self.media_player.positionChanged.connect(self.setTimeSlider)

        # Set volume slider
        self.volume_slider = QSlider(Qt.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(75)
        self.volume_slider.setValue(self.volume_init)
        self.volume_slider.setSingleStep(5)
        self.volume_slider.sliderMoved.connect(self.setPlayerVolume)
        self.media_player.volumeChanged.connect(self.setVolumeSlider)

        # Set control layout
        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(5, 0, 5, 0)
        controlLayout.addWidget(self.play_button)
        controlLayout.addWidget(self.speed_button)
        controlLayout.addWidget(self.time_label)
        controlLayout.addWidget(self.time_slider)
        controlLayout.addWidget(self.volume_slider)

        # Set layout for video player
        vp_layout = QVBoxLayout()
        vp_layout.setContentsMargins(0, 0, 0, 0)
        vp_layout.addWidget(self.video_widget)
        vp_layout.addLayout(controlLayout)

        # Set widget for video player
        self.vp_widget = QWidget()
        self.vp_widget.setLayout(vp_layout)

    # Function to handle video clicked
    def onVideoClicked(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.playClicked()
    
    # Function to handle play/pause button
    def playClicked(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            self.media_player.play()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

    # Function to handle speed button
    # Pressing will cycle through 1x, 2x, 4x, 1x, ...
    def speedClicked(self):
        if self.media_player.playbackRate() == 1:
            self.media_player.setPlaybackRate(2)
            self.speed_button.setText("2x")
        elif self.media_player.playbackRate() == 2:
            self.media_player.setPlaybackRate(4)
            self.speed_button.setText("4x")
        elif self.media_player.playbackRate() == 4:
            self.media_player.setPlaybackRate(1)
            self.speed_button.setText("1x")

    # Function to update time label
    def updateTimeLabel(self, position):
        if self.media_player.duration() > 3600000:
            current_time = QTime((position // 3600000) % 60, (position // 60000) % 60, (position // 1000) % 60)
            duration = QTime((self.media_player.duration() // 3600000) % 60, (self.media_player.duration() // 60000) % 60, (self.media_player.duration() // 1000) % 60)
            self.time_label.setText(current_time.toString('hh:mm:ss') + ' / ' + duration.toString('hh:mm:ss'))
        else:
            current_time = QTime(0, (position // 60000) % 60, (position // 1000) % 60)
            duration = QTime(0, (self.media_player.duration() // 60000) % 60, (self.media_player.duration() // 1000) % 60)
            self.time_label.setText(current_time.toString('mm:ss') + ' / ' + duration.toString('mm:ss'))
        self.time_slider.setRange(0, self.media_player.duration())

    # Function to set player position from time slider
    def setPlayerPos(self, position):
        self.media_player.setPosition(position)
        self.updateTimeLabel(position)

    # Function to set time slider from player position
    def setTimeSlider(self, position):
        self.time_slider.setValue(position)
        self.updateTimeLabel(position)

    # Function to set player volume from volume slider
    def setPlayerVolume(self, volume):
        self.media_player.setVolume(volume)
        self.last_volume = volume

    # Function to set volume slider from player volume
    def setVolumeSlider(self, volume):
        self.volume_slider.setValue(volume)

    # Function to move forward by mstime
    def moveForward(self, mstime=1000):
        if self.media_player.position() + mstime > self.media_player.duration():
            self.media_player.setPosition(self.media_player.duration())
            self.updateTimeLabel(self.media_player.duration())
            self.setPlayerPos(self.media_player.duration())
        else:
            self.media_player.setPosition(self.media_player.position() + mstime)
            self.updateTimeLabel(self.media_player.position() + mstime)
            self.setPlayerPos(self.media_player.position() + mstime)

    # Function to move backward by mstime
    def moveBackward(self, mstime=1000):
        if self.media_player.position() - mstime < 0:
            self.media_player.setPosition(0)
            self.updateTimeLabel(0)
            self.setPlayerPos(0)
        else:
            self.media_player.setPosition(self.media_player.position() - mstime)
            self.updateTimeLabel(self.media_player.position() - mstime)
            self.setPlayerPos(self.media_player.position() - mstime)

    # Function to increase volume by percent
    def increaseVolume(self, percent=5):
        if self.media_player.volume() + percent > 100:
            self.media_player.setVolume(100)
            self.setVolumeSlider(100)
            self.setPlayerVolume(100)
        else:
            self.media_player.setVolume(self.media_player.volume() + percent)
            self.setVolumeSlider(self.media_player.volume() + percent)
            self.setPlayerVolume(self.media_player.volume() + percent)

    # Function to decrease volume by percent
    def decreaseVolume(self, percent=5):
        if self.media_player.volume() - percent < 0:
            self.media_player.setVolume(0)
            self.setVolumeSlider(0)
            self.setPlayerVolume(0)
        else:
            self.media_player.setVolume(self.media_player.volume() - percent)
            self.setVolumeSlider(self.media_player.volume() - percent)
            self.setPlayerVolume(self.media_player.volume() - percent)


class Extractor(QWidget):

    def __init__(self, parent=None):
        super(Extractor, self).__init__(parent)
        self.initUI()

    def initUI(self):

        self.extract_button = QPushButton('Extract', self)
        self.remove_extracted_button = QPushButton('Remove Extracted', self)
        self.extract_layout = QVBoxLayout()
        self.extract_layout.setAlignment(Qt.AlignCenter)
        self.extract_layout.addWidget(self.extract_button)
        self.extract_layout.addWidget(self.remove_extracted_button)

        self.setLayout(self.extract_layout)


class Tagger(QWidget):

    def __init__(self, parent=None):
        super(Tagger, self).__init__(parent)
        self.initUI()

    def initUI(self):

        self.bestcheck = QCheckBox('Best', self)
        self.bestcheck.stateChanged.connect(self.onBestCheckChanged)

        tag_layout = QVBoxLayout()
        tag_layout.setAlignment(Qt.AlignCenter)
        tag_layout.addWidget(self.bestcheck)

        self.setLayout(tag_layout)

    def onBestCheckChanged(self, event):
        if event == Qt.Checked:
            print('Checked')
        else:
            print('Unchecked')


class MainWindow(QWidget):

    def __init__(self):
        super(MainWindow, self).__init__()
        os.makedirs('data/', exist_ok=True)
        os.makedirs('logs/', exist_ok=True)
        if not os.path.exists('data/best_tags.json'):
            with open('data/best_tags.json', 'w') as f:
                json.dump({}, f)
        if not os.path.exists('logs/logs.json'):
            with open('logs/logs.json', 'w') as f:
                defaults = {'window_geoms': [100, 100, 1000, 500],
                            'column_widths': [300, 0 , 150, 0],
                            'last_dir': '.'}
                json.dump(defaults, f)
        self.initUI()

    def initUI(self):

        self.filetree = FileTree()
        self.media = MediaDisplay()
        self.extractor = Extractor()
        self.tagger = Tagger()

        # Connect signals to number key presses here
        self.filetree.tree_clicked.connect(self.onTreeClicked)
        self.filetree.selection_changed.connect(self.onSelectionChanged)
        self.filetree.section_resized.connect(self.onSectionResized)

        self.extractor.extract_button.clicked.connect(self.onExtractClicked)
        self.extractor.remove_extracted_button.clicked.connect(self.onRemoveExtractedClicked)

        ####### Main ########
        with open('data/best_tags.json', 'r') as f:
            self.sc_tags = json.load(f)
            self.sc_keys = list(self.sc_tags.keys())
        
        # Paths list to display ticks in filetree
        self.paths_list = []
        for key in self.sc_keys:
            self.paths_list.append(os.path.basename(key))
        self.filetree.file_model.updatePaths(self.paths_list)

        with open('logs/logs.json', 'r') as f:
            self.logs = json.load(f)

        self.splitter1 = QSplitter(Qt.Horizontal)
        self.splitter1.addWidget(self.filetree)
        self.splitter1.addWidget(self.media.image_widget)
        self.splitter1.setSizes([400, 900])
        print(self.splitter1.sizes())
        self.splitter1.splitterMoved.connect(self.splitter1Moved)

        self.splitter2 = QSplitter(Qt.Horizontal)
        self.splitter2.addWidget(self.extractor)
        self.splitter2.addWidget(self.tagger)
        self.splitter2.setSizes(self.splitter1.sizes())
        print(self.splitter2.sizes())
        self.splitter2.splitterMoved.connect(self.splitter2Moved)

        self.splitter3 = QSplitter(Qt.Vertical)
        self.splitter3.addWidget(self.splitter1)
        self.splitter3.addWidget(self.splitter2)
        self.splitter3.setSizes([500, 100])

        self.main_layout = QVBoxLayout(self)
        # self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.splitter3)

        self.setLayout(self.main_layout)
        x, y, w, h = self.logs['window_geoms']
        self.setGeometry(x, y, w, h)

        ##### Shortcuts #####
        self.shortcut = QShortcut(QKeySequence(Qt.Key_1), self)
        # self.shortcut.activated.connect(self.onKey1)
        self.shortcut = QShortcut(QKeySequence(Qt.Key_2), self)
        # self.shortcut.activated.connect(self.onKey2)
        self.shortcut = QShortcut(QKeySequence(Qt.Key_3), self)
        # self.shortcut.activated.connect(self.onKey3)
        self.shortcut = QShortcut(QKeySequence(Qt.Key_5), self)
        self.shortcut.activated.connect(self.onKey5)
        self.shortcut = QShortcut(QKeySequence(Qt.Key_7), self)
        self.shortcut.activated.connect(self.onKey7)
        self.shortcut = QShortcut(QKeySequence(Qt.Key_8), self)
        self.shortcut.activated.connect(self.onKey8)
        self.shortcut = QShortcut(QKeySequence(Qt.Key_9), self)
        self.shortcut.activated.connect(self.onKey9)
        self.shortcut = QShortcut(QKeySequence(Qt.Key_0), self)
        self.shortcut.activated.connect(self.onKey0)
        self.shortcut = QShortcut(QKeySequence(Qt.Key_Plus), self)
        self.shortcut.activated.connect(self.onKeyPlus)
        self.shortcut = QShortcut(QKeySequence(Qt.Key_Minus), self)
        self.shortcut.activated.connect(self.onKeyMinus)

        ##### Set Flags #####
        self.last_photo = True
        self.last_video = False
        self.video_displayed = False

        ####### Window #######
        QApplication.setStyle(QStyleFactory.create('Fusion'))
        self.setWindowTitle('Media Tagger')
        self.show()


    #### Shortcuts ####
    
    # Delete tags for current file
    def onKey5(self):
        if self.tagger.bestcheck.isChecked():
            self.tagger.bestcheck.setChecked(False)
            self.clearTags()
        else:
            self.saveTags()
            self.tagger.bestcheck.setChecked(True)

    def onKey7(self):
        self.media.moveBackward(1000)

    def onKey8(self):
        self.media.playClicked()

    def onKey9(self):
        self.media.moveForward(1000)
    
    def onKey0(self):
        self.reloadVideo()

    def onKeyPlus(self):
        self.media.increaseVolume(5)

    def onKeyMinus(self):
        self.media.decreaseVolume(5)

    #### Splitter ####

    def splitter1Moved(self, pos=None, index=None):
        sizes = self.splitter1.sizes()
        total = sum(sizes)
        sizes[1] = total - sizes[0]
        self.splitter2.setSizes(sizes)

    def splitter2Moved(self, pos=None, index=None):
        sizes = self.splitter2.sizes()
        total = sum(sizes)
        sizes[1] = total - sizes[0]
        self.splitter1.setSizes(sizes)

    #### Saving ####

    # Function to save tags
    def saveTags(self, clear=True):

        with open('data/best_tags.json', 'r') as f:
            self.sc_tags = json.load(f)
            self.sc_keys = list(self.sc_tags.keys())

        index = self.filetree.tree.selectedIndexes()[0]
        file_path = self.filetree.file_model.filePath(index)

        if os.path.basename(file_path) not in self.paths_list:
            self.paths_list.append(os.path.basename(file_path))

        dt = datetime.now().strftime("%y%m%d-%H%M")

        tags = {'Best': True,
                'DateSaved': dt}
        self.sc_tags[file_path] = tags

        with open('data/best_tags.json', 'w') as f:
            json.dump(self.sc_tags, f, indent=2)
        
        self.filetree.file_model.updatePaths(self.paths_list)

        # reset slider values
        if clear:
            self.tagger.bestcheck.setChecked(False)

    # Function to clear tags
    def clearTags(self):

        with open('data/best_tags.json', 'r') as f:
            self.sc_tags = json.load(f)
            self.sc_keys = list(self.sc_tags.keys())

        index = self.filetree.tree.selectedIndexes()[0]
        file_path = self.filetree.file_model.filePath(index)

        if os.path.basename(file_path) in self.paths_list:
            self.paths_list.remove(os.path.basename(file_path))

        self.sc_tags.pop(file_path)

        with open('data/best_tags.json', 'w') as f:
            json.dump(self.sc_tags, f, indent=2)
        
        self.filetree.file_model.updatePaths(self.paths_list)

        # reset slider values
        self.tagger.bestcheck.setChecked(False)

    # Function to save column geometry
    def onSectionResized(self, logicalIndex=None, oldSize=None, newSize=None):
        with open('logs/logs.json', 'r') as f:
            self.logs = json.load(f)

        column_widths = []
        for i in range(self.filetree.tree.model().columnCount()):
            column_widths.append(self.filetree.tree.columnWidth(i))
        column_widths[2] = 180
        self.logs['column_widths'] = column_widths

        with open('logs/logs.json', 'w') as f:
            json.dump(self.logs, f, indent=2)
        
    # Function to save window settings
    def saveWindowSettings(self):
        with open('logs/logs.json', 'r') as f:
            self.logs = json.load(f)

        window_geoms = []
        window_geoms.append(self.geometry().x())
        window_geoms.append(self.geometry().y())
        window_geoms.append(self.geometry().width())
        window_geoms.append(self.geometry().height())
        self.logs['window_geoms'] = window_geoms

        self.logs['last_dir'] = self.filetree.file_model.rootPath()
        print(f'Last dir: {self.filetree.file_model.rootPath()}')

        with open('logs/logs.json', 'w') as f:
            json.dump(self.logs, f, indent=2)

    # Function to save window settings
    def closeEvent(self, event):
        self.saveWindowSettings()

    # Function to close window
    def closeWindow(self):
        self.saveWindowSettings()
        self.close()

    #### Main ####

    def onSelectionChanged(self):
        selected_indexes = self.filetree.tree.selectedIndexes()
        if selected_indexes:
            selected_index = selected_indexes[0]
            self.onTreeClicked(selected_index)

    def onTreeClicked(self, index=None):

        index = self.filetree.tree.selectedIndexes()[0]
        file_path = self.filetree.file_model.filePath(index)
        print(f'Selected: {file_path}')

        # Check if the file is an image
        if file_path.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".svg")):

            if self.last_video:
                self.media.media_player.stop()
                self.splitter1.replaceWidget(1, self.media.image_widget)

            pixmap = QPixmap(file_path)
            pixmap = pixmap.scaled(self.media.image_label.size(), aspectRatioMode=Qt.KeepAspectRatio, transformMode=Qt.SmoothTransformation)
            self.media.image_label.setPixmap(pixmap)

            self.last_photo = True
            self.last_video = False
            self.video_displayed = False

        # Check if the file is a video
        elif file_path.endswith((".mp4", ".avi", ".mov", ".wmv", ".flv", ".mpeg", ".mpg", ".mkv", ".webm", ".3gp", ".ts", ".m4v", ".ogv", ".vob")):
            
            if self.last_photo:
                self.splitter1.replaceWidget(1, self.media.vp_widget)
                self.media.video_widget.setAspectRatioMode(1)

            self.media.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            media_content = QMediaContent(QUrl.fromLocalFile(file_path))
            self.media.media_player.setVolume(self.media.last_volume)
            self.media.media_player.setMedia(media_content)
            self.media.media_player.play()
            
            self.last_photo = False
            self.last_video = True
            self.video_displayed = True

        # Display black image if file is not an image or video
        else:
            if self.last_video:
                self.media.media_player.stop()
                self.splitter1.replaceWidget(1, self.media.image_widget)

            self.media.image_label.setPixmap(QPixmap("./icons/black.png"))

            self.last_photo = True
            self.last_video = False
            self.video_displayed = False

        # Update tagger sliders
        if file_path in self.sc_tags:
            self.tagger.bestcheck.setChecked(True)
        else:
            self.tagger.bestcheck.setChecked(False)

    # Function to reload video
    def reloadVideo(self):
        self.onTreeClicked()


    #### Controls ####

    # Function to handle wheel events
    def wheelEvent(self, event: QWheelEvent):
        if self.video_displayed:
            if event.angleDelta().y() > 0:
                if self.media.media_player.volume() < 95:
                    self.media.setPlayerVolume(self.media.media_player.volume() + 5)
                else:
                    self.media.setPlayerVolume(100)
            else:
                if self.media.media_player.volume() > 5:
                    self.media.setPlayerVolume(self.media.media_player.volume() - 5)
                else:
                    self.media.setPlayerVolume(0)

    #### Extractor ####
    # Extract best from current dir to <current dir>-best in parent dir
    def onExtractClicked(self):
        dir = self.filetree.file_model.rootPath()
        dir_name = os.path.basename(dir)
        dir_parent = os.path.dirname(dir)
        print(f'Extracting from: {dir}')
        with open('data/best_tags.json', 'r') as f:
            self.sc_tags = json.load(f)
        
        best_dirs = []
        for file_path in self.sc_tags:
            if not file_path.startswith(dir):
                continue
            if os.path.isdir(file_path):
                best_dirs.append(file_path)
                for root, dirs, files in os.walk(file_path):
                    for file in files:
                        rel_path = os.path.relpath(os.path.join(root, file), dir)
                        rel_dir = os.path.split(rel_path)[0]
                        print(f'Extracting: {os.path.join(root, file)}')
                        os.makedirs(f'{dir_parent}/{dir_name}-best', exist_ok=True)
                        os.makedirs(f'{dir_parent}/{dir_name}-best/{rel_dir}', exist_ok=True)
                        shutil.copy(os.path.join(root, file), f'{dir_parent}/{dir_name}-best/{rel_dir}')
            else:
                rel_path = os.path.relpath(file_path, dir)
                rel_dir = os.path.split(rel_path)[0]
                print(f'Extracting: {file_path}')
                os.makedirs(f'{dir_parent}/{dir_name}-best', exist_ok=True)
                os.makedirs(f'{dir_parent}/{dir_name}-best/{rel_dir}', exist_ok=True)
                shutil.copy(file_path, f'{dir_parent}/{dir_name}-best/{rel_dir}')
        print('Done!')

    def onRemoveExtractedClicked(self):
        dir = self.filetree.file_model.rootPath()
        dir_name = os.path.basename(dir)
        dir_parent = os.path.dirname(dir)
        print(f'Removing extracted from: {dir}')
        if os.path.exists(f'{dir_parent}/{dir_name}-best'):
            shutil.rmtree(f'{dir_parent}/{dir_name}-best')
        print('Done!')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()
