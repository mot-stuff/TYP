import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                          QSlider, QStyle, QLabel, QSizePolicy, QScrollArea, 
                          QTextBrowser, QToolTip, QApplication, QFileDialog) 
from PyQt5.QtCore import Qt, QTime, QUrl, QSize, QTimer, QRect, QThread, pyqtSignal, QMetaObject
from PyQt5.QtGui import QIcon, QPainter, QColor, QPixmap, QCursor
import vlc
import os
from core.file_explorer import FileExplorerDialog
from utils.Downloader import Downloader
import sys
import base64
import requests
# The video player class - absolute cancer to work with so goodluck!
class CustomVideoPlayer(QWidget):
    playbackFinished = pyqtSignal()  # Add signal definition

    def __init__(self):
        super().__init__()
        # Add always-on-top flag
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Header section with back button and title
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(50)  # Fixed height for header
        self.header_widget.setStyleSheet("background-color: #1A1A1A;")
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(15, 12, 15, 12)
        
        # Back button setup with correct path
        self.back_to_youtube = QPushButton()
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up one level to TYP folder
        icon_path = os.path.join(script_dir, 'images', 'backarrow.png')
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.back_to_youtube.setIcon(QIcon(scaled_pixmap))
        self.back_to_youtube.setIconSize(QSize(32, 32))
        self.back_to_youtube.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #FF0000;
                border-radius: 24px;
            }
        """)
        self.back_to_youtube.setCursor(Qt.PointingHandCursor)
        header_layout.addWidget(self.back_to_youtube)
        
        # Title label in header
        self.title_label = QLabel()
        self.title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                margin-left: 15px;
            }
            QLabel:hover {
                color: #FF0000;
            }
        """)
        self.title_label.setWordWrap(True)
        self.title_label.setCursor(Qt.PointingHandCursor)
        self.title_label.mousePressEvent = self.copy_video_url
        header_layout.addWidget(self.title_label, 1)

        # Add MP3 download button before the video download button
        self.mp3_button = QPushButton()
        self.mp3_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        self.mp3_button.setIconSize(QSize(24, 24))
        self.mp3_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #FF0000;
                border-radius: 16px;
            }
        """)
        self.mp3_button.setCursor(Qt.PointingHandCursor)
        self.mp3_button.setToolTip("Download MP3")
        self.mp3_button.clicked.connect(self.download_mp3)
        header_layout.addWidget(self.mp3_button)

        # Add download button to header
        self.download_button = QPushButton()
        self.download_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.download_button.setIconSize(QSize(24, 24))
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #FF0000;
                border-radius: 16px;
            }
        """)
        self.download_button.setCursor(Qt.PointingHandCursor)
        self.download_button.setToolTip("Download Video")
        self.download_button.clicked.connect(self.download_video)
        header_layout.addWidget(self.download_button)

        # Store both streaming and YouTube URLs
        self.current_video_url = ""
        self.youtube_url = ""

        # Add header to main layout
        self.layout.addWidget(self.header_widget)
        
        # Initialize VLC with adjusted parameters for smoother load:
        vlc_args = [
            '--audio-resampler=soxr',
            '--file-caching=1000',     # lowered caching value
            '--network-caching=1000',
            '--live-caching=1000',
            '--sout-mux-caching=1000',
            '--clock-jitter=0',
            '--clock-synchro=0',
            '--audio-desync=0',
            '--sout-keep',
            '--avcodec-hw=none'        # disable hardware acceleration for improved stability
        ]
        
        try:
            self.instance = vlc.Instance(' '.join(vlc_args))
            if not self.instance:
                self.instance = vlc.Instance()
            self.media_player = self.instance.media_player_new()
            
        except Exception as e:
            print(f"VLC initialization error: {str(e)}")
            self.instance = vlc.Instance()
            self.media_player = self.instance.media_player_new()
        
        # Set up event manager
        self.event_manager = self.media_player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_playback_finished)
        # Attach position-changed event to update slider continuously
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.on_position_changed)
        
        # Create container widget for VLC
        self.video_widget = QWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setMinimumHeight(500)
        
        # Set video widget to use its winId for VLC
        if sys.platform == "win32":
            self.media_player.set_hwnd(int(self.video_widget.winId()))
        else:
            self.media_player.set_xwindow(int(self.video_widget.winId()))
            
        self.layout.addWidget(self.video_widget, 1)
        
        # Timer for updating position slider
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self.update_position)
        
        # Optionally disable custom control events for testing:
        self.use_custom_controls = False  # Set to True to enable custom controls
        if self.use_custom_controls:
            # Add custom click handling to video widget
            self.video_widget.mousePressEvent = self.video_clicked
            # Add custom key press handling for fullscreen toggle
            self.video_widget.keyPressEvent = self.handle_key_press

        # Bottom container for controls, description, and comments
        bottom_container = QWidget()
        bottom_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        bottom_container.setStyleSheet("background-color: #1A1A1A;")  # Set background for container
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setSpacing(0)  # Remove spacing between elements
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Controls section first
        controls_container = QWidget()
        controls_container.setFixedHeight(50)
        controls_container.setStyleSheet("background-color: #1A1A1A;")
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(10, 5, 10, 5)
        
        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout()
        self.controls_widget.setLayout(self.controls_layout)
        
        # Define button style first
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #404040;
                border-radius: 15px;
            }
            QPushButton QIcon {
                color: white;
            }
        """
        
        # Create time labels
        self.time_label = QLabel("0:00")
        self.duration_label = QLabel("0:00")
        
        # Create control buttons
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.play_pause)
        
        self.back_button = QPushButton()
        self.back_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.back_button.clicked.connect(lambda: self.seek_relative(-10000))
        
        self.forward_button = QPushButton()
        self.forward_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.forward_button.clicked.connect(lambda: self.seek_relative(10000))
        
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.sliderPressed.connect(self.on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self.on_slider_released)
        self.seek_slider.sliderMoved.connect(self.on_slider_moved)  # NEW: update during scrubbing
        
        # Create volume controls
        self.volume_button = QPushButton()
        self.volume_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        self.volume_button.clicked.connect(self.toggle_mute)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self.set_volume)
        
        # Add fullscreen button after volume controls
        self.fullscreen_button = QPushButton()
        fullscreen_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images', 'fullscreen.png')
        if os.path.exists(fullscreen_icon_path):
            pixmap = QPixmap(fullscreen_icon_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.fullscreen_button.setIcon(QIcon(pixmap))
        else:
            self.fullscreen_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.controls_layout.addWidget(self.fullscreen_button)
        # NEW: Add theater mode button next to fullscreen
        self.theater_button = QPushButton()
        theater_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images', 'theater.png')
        if os.path.exists(theater_icon_path):
            pixmap = QPixmap(theater_icon_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.theater_button.setIcon(QIcon(pixmap))
        else:
            self.theater_button.setIcon(self.style().standardIcon(QStyle.SP_DesktopIcon))
        self.theater_button.setIconSize(QSize(32, 32))
        self.theater_button.setStyleSheet(button_style)
        self.theater_button.setCursor(Qt.PointingHandCursor)
        self.theater_button.setToolTip("Toggle Theater Mode")
        self.theater_button.clicked.connect(self.toggle_theater_mode)
        self.controls_layout.addWidget(self.theater_button)
        
        # Update controls layout (modify this section to put icons in correct order)
        self.controls_layout.addWidget(self.play_button)
        self.controls_layout.addWidget(self.back_button)
        self.controls_layout.addWidget(self.time_label)
        self.controls_layout.addWidget(self.seek_slider)
        self.controls_layout.addWidget(self.duration_label)
        self.controls_layout.addWidget(self.forward_button)
        self.controls_layout.addWidget(self.volume_button)
        self.controls_layout.addWidget(self.volume_slider)
        # Move theater and fullscreen buttons to end
        self.controls_layout.addWidget(self.theater_button)
        self.controls_layout.addWidget(self.fullscreen_button)
        
        # Add controls to bottom layout first
        controls_layout.addWidget(self.controls_widget)
        bottom_layout.addWidget(controls_container)
        
        # Description section second
        self.description_widget = QWidget()
        self.description_widget.setStyleSheet("background-color: #1A1A1A;")
        description_layout = QVBoxLayout(self.description_widget)
        description_layout.setContentsMargins(15, 0, 15, 0)  # Remove vertical padding
        
        self.description_box = QTextBrowser()
        self.description_box.setStyleSheet("""
            QTextBrowser {
                background-color: #1A1A1A;
                color: white;
                border: 1px solid #FFFFFF;
                font-size: 12px;
                line-height: 1.3;
                padding: 0px;
                margin: 0px;
            }
            QTextBrowser:focus {
                outline: none;
                border: none;
            }
        """)
        self.description_box.setFrameShape(QTextBrowser.NoFrame)  # Remove frame completely
        self.description_box.setFixedHeight(60)  # Fixed height for description
        description_layout.addWidget(self.description_box)
        bottom_layout.addWidget(self.description_widget)
        
        # Comments section last
        comments_container = QWidget()
        comments_container.setFixedHeight(100)  # Reduced height from 150
        comments_container.setStyleSheet("background-color: #1A1A1A;")
        comments_layout = QVBoxLayout(comments_container)
        comments_layout.setContentsMargins(15, 0, 15, 0)  # Remove vertical padding
        
        self.comments_area = QTextBrowser()
        self.comments_area.setMaximumHeight(90)  # Reduced from 150
        self.comments_area.setStyleSheet("""
            QTextBrowser {
                background-color: #282828;
                color: white;
                border: none;
                padding: 8px;
            }
        """)
        comments_layout.addWidget(self.comments_area)
        bottom_layout.addWidget(comments_container)
        
        self.layout.addWidget(bottom_container)
        
        # Initialize fullscreen state
        self.is_fullscreen = False

        # Initialize volume state
        self.previous_volume = 100
        self.media_player.audio_set_volume(100)

        # Update control buttons styling
        self.play_button.setStyleSheet(button_style)
        self.back_button.setStyleSheet(button_style)
        self.forward_button.setStyleSheet(button_style)
        self.volume_button.setStyleSheet(button_style)
        self.fullscreen_button.setStyleSheet(button_style)
        
        # Make control icons white
        self.set_white_icon = lambda button, icon_type: self._create_white_icon(button, icon_type)
        
        self.set_white_icon(self.back_button, QStyle.SP_MediaSkipBackward)
        self.set_white_icon(self.forward_button, QStyle.SP_MediaSkipForward)
        self.set_white_icon(self.volume_button, QStyle.SP_MediaVolume)
        
        # Style time labels
        time_label_style = "QLabel { color: white; }"
        self.time_label.setStyleSheet(time_label_style)
        self.duration_label.setStyleSheet(time_label_style)
        
        # Style seek slider
        self.seek_slider.setStyleSheet("""
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

        # Add buffering timer
        self.buffer_timer = QTimer()
        self.buffer_timer.setInterval(500)  # Check every 500ms
        self.buffer_timer.timeout.connect(self.check_buffering)
        self.is_buffering = False
        
        # Track last position for sync checking
        self.last_position = 0
        self.stall_count = 0

        self.last_seek_time = 0  # New attribute to track when user last sought
        self.consecutive_buffer_count = 0
        self.is_scrubbing = False

        # Bottom container for controls, description, and comments
        self.bottom_container = bottom_container  # NEW: store as attribute for theater adjustments
        # Replace local comments_container with an attribute:
        self.comments_container = comments_container  # NEW: enable toggling later

    def _create_white_icon(self, button, icon_type):
        """Helper method to create white icons"""
        icon = self.style().standardIcon(icon_type)
        pixmap = icon.pixmap(32, 32)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor('white'))
        painter.end()
        button.setIcon(QIcon(pixmap))

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode by reparenting the video widget."""
        if not self.is_fullscreen:
            self.video_widget.setWindowFlags(Qt.Window)
            self.video_widget.showFullScreen()
            self.header_widget.hide()
            self.controls_widget.hide()
            self.description_widget.hide()
            self.comments_area.hide()
            self.set_white_icon(self.fullscreen_button, QStyle.SP_TitleBarNormalButton)
            self.is_fullscreen = True
        else:
            self.video_widget.setWindowFlags(Qt.Widget)
            self.video_widget.showNormal()
            self.header_widget.show()
            self.controls_widget.show()
            self.description_widget.show()
            self.comments_area.show()
            self.set_white_icon(self.fullscreen_button, QStyle.SP_TitleBarMaxButton)
            self.is_fullscreen = False

    def handle_key_press(self, event):
        """Handle keyboard events for toggling fullscreen."""
        if event.key() in (Qt.Key_Escape, Qt.Key_F):
            if self.is_fullscreen:
                self.toggle_fullscreen()
                event.accept()
            else:
                # Allow toggling on fullscreen by pressing F if not already in fullscreen.
                self.toggle_fullscreen()
                event.accept()
        else:
            event.ignore()

    def video_clicked(self, event):
        """Handle mouse clicks on video"""
        if event.button() == Qt.LeftButton:
            self.play_pause()
        event.accept()

    def format_time(self, ms):
        total_seconds = int(ms / 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    def play_pause(self):
        if self.media_player.is_playing():
            self.media_player.pause()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.update_timer.stop()
        else:
            self.media_player.play()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.update_timer.start()

    def seek_relative(self, offset_ms):
        """Seek relative to current position"""
        try:
            current = self.media_player.get_time()
            if current >= 0:
                target = max(0, current + offset_ms)
                self.seek_to_time(target)
        except Exception as e:
            print(f"Relative seek error: {str(e)}")

    def seek_to_time(self, time_ms):
        """Seek to absolute time in milliseconds"""
        try:
            length = self.media_player.get_length()
            if length > 0:
                # Keep within bounds
                time_ms = max(0, min(time_ms, length))
                self.media_player.set_time(time_ms)
        except Exception as e:
            print(f"Absolute seek error: {str(e)}")

    def set_position(self, position):
        """Seek to the absolute time (in ms) from the slider value"""
        try:
            self.seek_to_time(position)
            self.last_seek_time = time.time()  # Update whenever user seeks
        except Exception as e:
            print(f"Set position error: {str(e)}")

    def on_slider_pressed(self):
        self.is_scrubbing = True
        self.last_seek_time = time.time()  # Mark the start of scrubbing

    def on_slider_released(self):
        value = self.seek_slider.value()
        self.set_position(value)
        self.is_scrubbing = False
        # Resume playback if not playing
        if not self.media_player.is_playing():
            self.media_player.play()

    def on_slider_moved(self, value):
        """Set video time continuously during scrubbing."""
        if self.is_scrubbing:
            self.media_player.set_time(value)
            self.time_label.setText(self.format_time(value))

    def update_position(self):
        if not self.media_player.is_playing() or self.is_scrubbing:
            return
        # New: check if VLC has reached an ended state (for streaming videos that eventually end)
        if not self.is_live and self.media_player.get_state() == vlc.State.Ended:
            self.on_playback_finished(None)
            return
        try:
            current_time = self.media_player.get_time()
            if self.is_live:
                return
            total_length = self.media_player.get_length()
            if current_time >= 0 and total_length > 0:
                self.seek_slider.blockSignals(True)
                self.seek_slider.setMaximum(total_length)
                self.seek_slider.setValue(current_time)
                self.seek_slider.blockSignals(False)
                self.time_label.setText(self.format_time(current_time))
                self.duration_label.setText(self.format_time(total_length))
                if not self.is_live and current_time >= total_length - 500:
                    self.stop()
                    self.hide()
                    self.playbackFinished.emit()
                    return
                if current_time % 5000 == 0:
                    tracks = self.media_player.audio_get_track_description()
                    if tracks and self.media_player.audio_get_track() <= 0:
                        self.media_player.audio_set_track(1)
        except Exception as e:
            print(f"Position update error: {e}")

    def on_position_changed(self, event):
        # Update slider based on VLC position events
        current_time = self.media_player.get_time()
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(current_time)
        self.seek_slider.blockSignals(False)

    def set_volume(self, volume):
        self.media_player.audio_set_volume(volume)

    def toggle_mute(self):
        is_muted = self.media_player.audio_get_mute()
        self.media_player.audio_set_mute(not is_muted)
        self.update_volume_ui(0 if not is_muted else self.previous_volume)

    def update_volume_ui(self, volume):
        self.volume_slider.setValue(volume)
        if volume > 0:
            icon_type = QStyle.SP_MediaVolume if volume > 50 else QStyle.SP_MediaVolumeMuted
            pixmap = self.style().standardIcon(icon_type).pixmap(32, 32)
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), QColor('white'))
            painter.end()
            self.volume_button.setIcon(QIcon(pixmap))
        else:
            icon = self.style().standardIcon(QStyle.SP_MediaVolumeMuted)
            pixmap = icon.pixmap(32, 32)
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), QColor('white'))
            painter.end()
            self.volume_button.setIcon(QIcon(pixmap))

    def update_comments(self, comments):
        self.comments_area.clear()
        if not comments:
            self.comments_area.setText("No comments available")
            return
            
        # Prepare HTML template with styling for author thumbnail
        html_template = """
        <style>
            body {
                font-family: Arial, sans-serif;
                color: #FFFFFF;
                background-color: #282828;
                margin: 0;
                padding: 10px;
            }
            .comment {
                background: #333;
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 10px;
            }
            .comment-header {
                display: flex;
                align-items: center;
            }
            .thumb {
                margin-right: 5px;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                vertical-align: middle;
            }
            .author {
                font-weight: bold;
                color: #FF4500;
                margin-right: 5px;
            }
            .likes {
                color: #AAAAAA;
                font-size: 12px;
            }
            .text {
                margin-top: 5px;
                line-height: 1.5;
            }
        </style>
        """
        
        def get_data_uri(url):
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    data = base64.b64encode(response.content).decode("utf-8")
                    mime = response.headers.get("Content-Type", "image/png")
                    return f"data:{mime};base64,{data}"
            except Exception as e:
                print(f"Error fetching image: {e}")
            return "https://via.placeholder.com/40"

        # Build comments HTML with thumbnail conversion
        comments_html = []
        for comment in comments[:10]:
            author = comment.get('author', 'Anonymous')
            text = comment.get('text', '').replace('\n', '<br>')
            likes = comment.get('like_count', 0)
            thumb_url = comment.get('author_thumbnail', '')
            thumb = get_data_uri(thumb_url) if thumb_url else "https://via.placeholder.com/20"
            
            comments_html.append(f"""
                <div class="comment">
                    <div class="comment-header">
                        <img class="thumb" src="{thumb}" alt="thumbnail" width="20" height="20"/>
                        <span class="author">{author}</span>
                        <span class="likes">• {likes} likes</span>
                    </div>
                    <div class="text">{text}</div>
                </div>
            """)
        
        full_html = html_template + ''.join(comments_html)
        self.comments_area.setHtml(full_html)

    def play_video(self, stream_urls, youtube_url, is_live=False):
        try:
            self.current_video_url = stream_urls[0]
            self.youtube_url = youtube_url
            self.is_live = is_live

            if is_live:
                media_opts = [
                    ":demux=hls",
                    ":live-caching=5000",
                    ":hls-live-edge=9999"
                ]
            else:
                # For VOD, expect dual-stream URLs from yt-dlp
                media_opts = []
            media = self.instance.media_new(stream_urls[0])
            # Use bestaudio URL if provided (dual stream 1080p)
            if len(stream_urls) > 1:
                media.add_option(f":input-slave={stream_urls[1]}")
            for opt in media_opts:
                media.add_option(opt)
            self.media_player.set_media(media)
            self.media_player.audio_set_volume(self.volume_slider.value())
            self.media_player.play()

            # Force audio synchronization check after a longer delay
            QTimer.singleShot(3000, self.check_audio_sync)

            self.update_timer.start()
            self.comments_area.setText("Loading comments...")
            self.buffer_timer.start()
        except Exception as e:
            print(f"Playback error: {str(e)}")

    def check_audio_sync(self):
        """Check and adjust audio sync if needed"""
        if self.media_player.is_playing():
            video_pos = self.media_player.get_time()
            if video_pos > 0:
                # Reset audio timing if significantly out of sync
                self.media_player.set_time(video_pos)
                self.media_player.audio_set_delay(0)

    def stop(self):
        # Use invokeMethod to stop timers on the correct thread
        QMetaObject.invokeMethod(self.buffer_timer, "stop", Qt.QueuedConnection)
        QMetaObject.invokeMethod(self.update_timer, "stop", Qt.QueuedConnection)
        self.media_player.stop()

    def check_buffering(self):
        if self.is_live or self.is_scrubbing:
            self.last_position = self.media_player.get_time()
            return
        if not self.media_player.is_playing():
            return
        # Removed custom buffering handling; use VLC's default behavior instead.
        self.last_position = self.media_player.get_time()

    def resume_from_buffer(self):
        # Auto-resume is disabled; do nothing.
        pass

    def set_video_info(self, title, description):
        if (title):
            self.title_label.setText(title)
            self.title_label.setVisible(True)
        else:
            self.title_label.setVisible(False)
            
        if (description):
            formatted_description = description.replace('\n', '<br>')
            self.description_box.setHtml(f"""
                <style>
                    body {{ 
                        color: white;
                        margin: 0;
                        padding: 0;
                    }}
                    p {{ margin: 0 0 10px 0; }}
                </style>
                {formatted_description}
            """)
            self.description_widget.setVisible(True)
        else:
            self.description_widget.setVisible(False)

    def copy_video_url(self, event):
        """Copy video URL to clipboard and show tooltip"""
        try:
            if self.youtube_url:
                # Copy to clipboard
                clipboard = QApplication.clipboard()
                clipboard.setText(self.youtube_url)
                
                # Show tooltip
                QToolTip.showText(
                    QCursor.pos(),
                    "URL Copied!",
                    self.title_label,
                    QRect(),
                    4000
                )
        except Exception as e:
            print(f"Copy error: {str(e)}")
        
        event.accept()

    def get_back_button(self):
        return self.back_to_youtube

    def download_video(self):
        """Download the current video"""
        if not self.youtube_url:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.download_button.setEnabled(False)
        self.download_button.setToolTip("Downloading...")

        self.download_thread = Downloader(self.youtube_url, 'video')
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.start()

    def download_mp3(self):
        """Download the current video as MP3"""
        if not self.youtube_url:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.mp3_button.setEnabled(False)
        self.mp3_button.setToolTip("Downloading MP3...")

        self.mp3_thread = Downloader(self.youtube_url, 'mp3')
        self.mp3_thread.finished.connect(self.mp3_download_finished)
        self.mp3_thread.error.connect(self.download_error)
        self.mp3_thread.start()

    def download_finished(self):
        """Handle video download completion"""
        QApplication.restoreOverrideCursor()
        self.download_button.setEnabled(True)
        self.download_button.setToolTip("Download Complete!")
        
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up one level to TYP folder
        downloads_dir = os.path.join(script_dir, 'downloads')
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
        dialog = FileExplorerDialog(downloads_dir, "Downloaded Videos", self)
        dialog.exec_()
        
        QTimer.singleShot(3000, lambda: self.download_button.setToolTip("Download Video"))

    def mp3_download_finished(self):
        """Handle MP3 download completion"""
        QApplication.restoreOverrideCursor()
        self.mp3_button.setEnabled(True)
        self.mp3_button.setToolTip("MP3 Download Complete!")
        
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up one level to TYP folder
        mp3_dir = os.path.join(script_dir, 'mp3')
        if not os.path.exists(mp3_dir):
            os.makedirs(mp3_dir)
        dialog = FileExplorerDialog(mp3_dir, "Downloaded Audio", self)
        dialog.exec_()
        
        QTimer.singleShot(3000, lambda: self.mp3_button.setToolTip("Download MP3"))

    def download_error(self, error_message):
        """Handle download errors"""
        QApplication.restoreOverrideCursor()
        self.download_button.setEnabled(True)
        self.mp3_button.setEnabled(True)
        print(f"Download error: {error_message}")

    def on_playback_finished(self, event):
        # VLC's MediaPlayerEndReached event triggers this method.
        self.stop()
        self.update_timer.stop()
        self.playbackFinished.emit()  # Notifies the parent to revert to YouTube view
        time.sleep(1)
        back_button = self.get_back_button()
        if back_button:
            back_button.click()
        self.hide()

    def toggle_theater_mode(self):
        """Toggle theater mode by showing/hiding elements and adjusting layout"""
        if not hasattr(self, 'is_theater_mode'):
            self.is_theater_mode = False
            # Store original height for restoration
            self.original_height = self.bottom_container.height()

        if not self.is_theater_mode:
            self.is_theater_mode = True
            self.description_widget.hide()
            self.comments_container.hide()
            # Adjust bottom container to contain only controls
            self.bottom_container.setFixedHeight(50)  # Fixed control height
            self.theater_button.setToolTip("Exit Theater Mode")
        else:
            self.is_theater_mode = False
            self.description_widget.show()
            self.comments_container.show()
            # Restore original layout
            self.bottom_container.setFixedHeight(self.original_height)
            self.theater_button.setToolTip("Theater Mode")
        
        # Force layout update
        self.bottom_container.updateGeometry()
        self.layout.update()