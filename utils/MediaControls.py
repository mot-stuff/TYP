from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSlider, QStyle
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPainter, QColor

class MediaControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # Create method to make icons white
        def create_white_icon(icon_type):
            icon = self.style().standardIcon(icon_type)
            pixmap = icon.pixmap(24, 24)  # Smaller size for media controls
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), QColor('white'))
            painter.end()
            return QIcon(pixmap)
        
        # Play/Pause button with white icon
        self.play_button = QPushButton()
        self.play_button.setIcon(create_white_icon(QStyle.SP_MediaPlay))
        
        # Time labels and slider
        self.time_label = QLabel("0:00")
        self.duration_label = QLabel("0:00")
        self.seek_slider = QSlider(Qt.Horizontal)
        
        # Volume controls with white icon
        self.volume_button = QPushButton()
        self.volume_button.setIcon(create_white_icon(QStyle.SP_MediaVolume))
        
        # Store create_white_icon method for later use
        self.create_white_icon = create_white_icon
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        
        # Add widgets to layout
        layout.addWidget(self.play_button)
        layout.addWidget(self.time_label)
        layout.addWidget(self.seek_slider)
        layout.addWidget(self.duration_label)
        layout.addWidget(self.volume_button)
        layout.addWidget(self.volume_slider)
        
        # Style
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background: #404040;
                border-radius: 15px;
            }
            QLabel {
                color: white;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 4px;
                background: #4A4A4A;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #FF0000;
            }
        """)
