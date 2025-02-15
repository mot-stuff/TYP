from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QLabel, 
                           QPushButton, QHBoxLayout, QFileIconProvider, 
                           QListWidgetItem, QStyle, QSlider, QWidget, QMessageBox)
from PyQt5.QtCore import Qt, QSize, QUrl, QTimer
from PyQt5.QtGui import QIcon, QPainter, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from utils.MediaControls import MediaControls
import os

class FileExplorerDialog(QDialog):
    def __init__(self, directory, title="Files", parent=None):
        super().__init__(parent)
        self.directory = directory
        self.setWindowTitle(title)
        self.setMinimumSize(500, 400)
        
        # Media player setup
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.media_controls = MediaControls()
        self.is_playing_video = False
        
        # Connect media player signals
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.stateChanged.connect(self.media_state_changed)
        
        # Connect control signals
        self.media_controls.play_button.clicked.connect(self.play_pause)
        self.media_controls.seek_slider.sliderMoved.connect(self.set_position)
        self.media_controls.volume_slider.valueChanged.connect(self.media_player.setVolume)
        self.media_controls.volume_button.clicked.connect(self.toggle_mute)
        
        self.setup_ui()
        self.load_files()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with path
        self.path_label = QLabel(self.directory)
        self.path_label.setStyleSheet("color: white; padding: 5px;")
        layout.addWidget(self.path_label)
        
        # Create a splitter for file list and media section
        self.file_list_widget = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_list_widget)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SingleSelection)
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #282828;
                border: none;
                color: white;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #FF0000;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
        """)
        self.file_list.itemDoubleClicked.connect(self.open_file)
        self.file_list_layout.addWidget(self.file_list)
        
        # Create media container
        self.media_container = QWidget()
        self.media_layout = QVBoxLayout(self.media_container)
        self.media_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add video widget to media container
        self.video_widget.setMinimumHeight(300)  # Set minimum height for video
        self.media_layout.addWidget(self.video_widget)
        self.media_layout.addWidget(self.media_controls)
        
        # Hide media container initially
        self.media_container.hide()
        
        # Add widgets to main layout
        layout.addWidget(self.file_list_widget)
        layout.addWidget(self.media_container)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.open_button = QPushButton("Open")
        self.delete_button = QPushButton("Delete")  # Add delete button
        self.close_button = QPushButton("Close")
        
        self.open_button.clicked.connect(self.open_selected)
        self.delete_button.clicked.connect(self.delete_selected)  # Connect delete action
        self.close_button.clicked.connect(self.close)
        
        button_style = """
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FF0000;
            }
        """
        
        self.open_button.setStyleSheet(button_style)
        self.delete_button.setStyleSheet(button_style)
        self.close_button.setStyleSheet(button_style)
        
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        # Dialog styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1A1A;
            }
        """)

    def load_files(self):
        self.file_list.clear()
        icon_provider = QFileIconProvider()
        
        try:
            files = os.listdir(self.directory)
            files.sort()
            
            for file in files:
                full_path = os.path.join(self.directory, file)
                item = QListWidgetItem(file)  # Fixed: QListWidgetItem instead of QListWidget.Item
                
                # Get proper file icon based on file type
                file_info = QFileIconProvider().icon(QFileIconProvider.File)
                if os.path.isfile(full_path):
                    if file.lower().endswith('.mp4'):
                        item.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                    elif file.lower().endswith('.mp3'):
                        item.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
                    else:
                        item.setIcon(file_info)
                
                self.file_list.addItem(item)
                
        except Exception as e:
            print(f"Error loading files: {str(e)}")

    def open_file(self, item):
        file_path = os.path.join(self.directory, item.text())
        if file_path.lower().endswith(('.mp3', '.mp4')):
            self.play_media(file_path)
        else:
            os.startfile(file_path)

    def play_media(self, file_path):
        # Stop any current playback
        self.media_player.stop()
        
        # Set up media
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.media_player.setVolume(self.media_controls.volume_slider.value())
        
        # Show appropriate widgets
        self.is_playing_video = file_path.lower().endswith('.mp4')
        
        # Adjust layout for video or audio
        if self.is_playing_video:
            self.video_widget.show()
            self.media_player.setVideoOutput(self.video_widget)
            self.setMinimumSize(800, 600)
            self.file_list_widget.setMaximumHeight(200)  # Shrink file list
        else:
            self.video_widget.hide()
            self.setMinimumSize(500, 400)
            self.file_list_widget.setMaximumHeight(16777215)  # Reset file list height
        
        self.media_container.show()
        self.media_controls.show()
        self.media_player.play()
        
        # Adjust layout after showing video
        if self.is_playing_video:
            QTimer.singleShot(100, self.adjust_layout)

    def adjust_layout(self):
        """Adjust layout after video starts playing"""
        self.video_widget.setMinimumHeight(300)
        self.updateGeometry()
        self.adjustSize()

    def play_pause(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def media_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.media_controls.play_button.setIcon(
                self.media_controls.create_white_icon(QStyle.SP_MediaPause)
            )
        else:
            self.media_controls.play_button.setIcon(
                self.media_controls.create_white_icon(QStyle.SP_MediaPlay)
            )

    def position_changed(self, position):
        self.media_controls.seek_slider.setValue(position)
        self.media_controls.time_label.setText(self.format_time(position))

    def duration_changed(self, duration):
        self.media_controls.seek_slider.setRange(0, duration)
        self.media_controls.duration_label.setText(self.format_time(duration))

    def set_position(self, position):
        self.media_player.setPosition(position)

    def toggle_mute(self):
        if self.media_player.volume() > 0:
            self.media_player.setVolume(0)
            self.media_controls.volume_button.setIcon(
                self.media_controls.create_white_icon(QStyle.SP_MediaVolumeMuted)
            )
        else:
            self.media_player.setVolume(self.media_controls.volume_slider.value())
            self.media_controls.volume_button.setIcon(
                self.media_controls.create_white_icon(QStyle.SP_MediaVolume)
            )

    def format_time(self, ms):
        total_seconds = int(ms / 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    def closeEvent(self, event):
        self.media_player.stop()
        super().closeEvent(event)

    def open_selected(self):
        if self.file_list.currentItem():
            self.open_file(self.file_list.currentItem())

    def delete_selected(self):
        """Delete the selected file with confirmation"""
        current_item = self.file_list.currentItem()
        if not current_item:
            return
            
        file_path = os.path.join(self.directory, current_item.text())
        
        # Show confirmation dialog
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirm Delete")
        msg.setText(f"Are you sure you want to delete\n{current_item.text()}?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setIcon(QMessageBox.Warning)
        
        # Style the message box
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #282828;
            }
            QMessageBox QLabel {
                color: white;
            }
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FF0000;
            }
        """)
        
        if msg.exec_() == QMessageBox.Yes:
            try:
                if os.path.exists(file_path):
                    # Stop playback if this is the current file
                    if self.media_player.state() != QMediaPlayer.StoppedState:
                        current_media = self.media_player.media().canonicalUrl().toLocalFile()
                        if current_media == file_path:
                            self.media_player.stop()
                            self.media_container.hide()
                    
                    # Delete the file
                    os.remove(file_path)
                    
                    # Remove from list
                    self.file_list.takeItem(self.file_list.row(current_item))
                    
            except Exception as e:
                error_msg = QMessageBox(self)
                error_msg.setWindowTitle("Error")
                error_msg.setText(f"Error deleting file:\n{str(e)}")
                error_msg.setIcon(QMessageBox.Critical)
                error_msg.setStyleSheet(msg.styleSheet())
                error_msg.exec_()
