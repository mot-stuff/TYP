import sys
import re
import logging
import os
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QMenu, QToolButton
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt5.QtCore import QUrl, QEventLoop, QTimer, QStandardPaths, QThread, pyqtSignal, QThreadPool, Qt, QSize
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtGui import QFont, QIcon, QPixmap
import yt_dlp
from core.video_player import CustomVideoPlayer
from core.file_explorer import FileExplorerDialog
from utils.URLIntercept import URLInterceptor 
from utils.CustomPermissions import CustomWebPage
from utils.CommentFetcher import CommentFetcher
# =============================================
#   _______  __     __  _____  
#  |__   __| \ \   / / |  __ \ 
#     | |     \ \_/ /  | |__) |
#     | |      \   /   |  ___/ 
#     | |       | |    | |     
#     |_|       |_|    |_|     
#                               
#      Tom's YouTube Premium
# =============================================
# An application created to not have to pay for YouTube Premium and 
# still get the benefits of it. Plus added downloader features for videos and audio.
# Created by: Tom
# Version: 1.0
# Stores cookies/cache in the AppData folder
# =============================================

class YouTubeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        # Set window icon - use correct relative path
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(script_dir, 'images', 'logo.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Logo not found at: {icon_path}")
            
        self.setWindowTitle("TYP - Tom's YouTube Player")
        self.setGeometry(100, 100, 1200, 800)

        # Create main winodw and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        profile = QWebEngineProfile.defaultProfile()
        
        # Set up storage paths
        data_path = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        cache_path = data_path + "/cache"
        
        # Configure profile settings - stackoverlowed
        profile.setCachePath(cache_path)
        profile.setPersistentStoragePath(data_path)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
        profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        profile.setHttpCacheMaximumSize(100 * 1024 * 1024)  # 100MB cache
        
        # Add URL interceptor to grab video URLs
        self.interceptor = URLInterceptor(self)
        profile.setUrlRequestInterceptor(self.interceptor)
        
        # Create web view widget with custom settings - sets the background page to the video so we make sure to get data to yt algo
        self.browser = QWebEngineView()
        self.custom_page = CustomWebPage(profile, self.browser)
        self.browser.setPage(self.custom_page)
        
        # Updated dark mode injection that won't block loading
        dark_mode_js = """
        function initDarkMode() {
            // Force dark mode preference
            if (document.cookie.indexOf('PREF=') < 0) {
                document.cookie = 'PREF=f6=400;domain=.youtube.com;path=/;SameSite=Lax';
            }
            
            const darkStyles = document.createElement('style');
            darkStyles.textContent = `
                :root {
                    --yt-spec-base-background: #0f0f0f !important;
                    --yt-spec-raised-background: #212121 !important;
                    --yt-spec-menu-background: #282828 !important;
                    --yt-spec-text-primary: #fff !important;
                    --yt-spec-text-secondary: #aaa !important;
                    --yt-spec-brand-background-primary: #282828 !important;
                }
                html[dark] { background: #0f0f0f !important; }
                ytd-app { background: #0f0f0f !important; }
            `;
            
            // Safely append styles
            try {
                if (!document.getElementById('dark-mode-style')) {
                    darkStyles.id = 'dark-mode-style';
                    document.head.appendChild(darkStyles);
                }
                document.documentElement.setAttribute('dark', '');
            } catch (e) {
                console.warn('Dark mode style injection failed:', e);
            }
        }

        // Initialize after a short delay to ensure DOM is ready
        setTimeout(initDarkMode, 100);
        
        // Re-apply on dynamic navigation
        const observer = new MutationObserver((mutations) => {
            if (document.body) initDarkMode();
        });
        
        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
        """

        # Setup page load handling
        def on_load_finished(ok):
            if (ok):
                self.browser.page().runJavaScript(dark_mode_js)

        self.browser.loadFinished.connect(on_load_finished)
        
        # Configure page settings
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.AutoLoadImages, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, True)
        
        # Add audio control
        self.browser.page().setAudioMuted(False)
        
        self.browser.setUrl(QUrl("https://www.youtube.com"))
        self.browser.urlChanged.connect(self.url_changed)
        self.layout.addWidget(self.browser)
        
        # Create a menu button that overlays the browser that has options
        menu_button = QToolButton(self.browser)
        menu_button.setFixedSize(80, 40) 
        menu_button.setStyleSheet("""
            QToolButton {
                background-color: rgba(40, 40, 40, 0.7);
                color: white;
                border: none;
                padding: 8px 4px;
                border-radius: 3px;
                margin: 5px;
            }
            QToolButton:hover {
                background-color: rgba(255, 0, 0, 0.8);
            }
        """)
        menu_button.setText("Options")  # Menu Text
        menu_button.setFont(QFont("Verdana", 8))  # Menu Font
        
        # Create popup menu
        menu = QMenu(menu_button)
        menu.setStyleSheet("""
            QMenu {
                background-color: #282828;
                color: white;
                border: 1px solid #404040;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #FF0000;
            }
        """)
        
        # Add menu items
        show_videos_action = menu.addAction("Show Downloaded Videos")
        show_audio_action = menu.addAction("Show Downloaded Audio")
        menu.addSeparator()
        clear_data_action = menu.addAction("Clear Data")
        
        # Connect actions
        show_videos_action.triggered.connect(self.open_downloads_folder)
        show_audio_action.triggered.connect(self.open_audio_folder)
        clear_data_action.triggered.connect(self.clear_browser_data)
        menu_button.setMenu(menu)
        
        # Position the button in bottom-right corner
        def update_button_position():
            x = self.browser.width() - menu_button.width() - 10
            y = self.browser.height() - menu_button.height() - 10
            menu_button.move(x, y)
        
        # Update position when browser resizes
        self.browser.resizeEvent = lambda e: update_button_position()
        update_button_position()

        # Create video player
        self.video_player = CustomVideoPlayer()
        self.video_player.get_back_button().clicked.connect(self.return_to_youtube)
        self.layout.addWidget(self.video_player)
        self.video_player.hide()

        self.comment_cache = {}
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # Limit thread count

        # Add custom headers for requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

        # Update back button icon path
        self.back_to_youtube = QPushButton()
        icon_path = os.path.join(script_dir, 'images', 'backarrow.png')
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.back_to_youtube.setIcon(QIcon(scaled_pixmap))
        self.back_to_youtube.setIconSize(QSize(32, 32))

    def clear_browser_data(self):
        # Clear various types of browsing data
        profile = self.browser.page().profile()
        profile.clearAllVisitedLinks()
        profile.clearHttpCache()
        profile.cookieStore().deleteAllCookies()
        
        # Force refresh the page
        self.browser.setUrl(QUrl("https://www.youtube.com"))

    def return_to_youtube(self):
        self.browser.setUrl(QUrl("https://www.youtube.com")) # always goes back home
        self.video_player.hide()
        self.video_player.stop()
        time.sleep(1)
        self.browser.page().setAudioMuted(False) # not really needed but just in case
        self.browser.show()

    def extract_video_id(self, url):
        pattern = r'(?:youtube\.com\/watch\?v=|youtu.be\/)([^&\?\/]+)'
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def url_changed(self, url):
        video_id = self.extract_video_id(url.toString())
        # Ensure we detect a master M3U8 link for live streams:
        if "m3u8" in url.toString():
            # Example usage: pass the M3U8 link to the video player
            m3u8_link = url.toString()
            self.video_player.play_video([m3u8_link], m3u8_link, is_live=True)
            self.video_player.show()
            self.browser.hide()
            return
        if video_id:
            # Don't navigate away, just mute the browser
            self.browser.page().setAudioMuted(True)
            self.browser.setUrl(QUrl("https://www.youtube.com")) # always goes back home
            # Then start the video download process
            self.download_and_play_video(video_id)

    def pause_browser_video(self):
        """Pause any background video playing in the browser."""
        self.browser.page().runJavaScript(
            "document.querySelectorAll('video').forEach(v => { v.pause(); v.currentTime = 0; });"
        )
    
    def download_and_play_video(self, video_id):
        try:
            # Prevent background playback:
            self.pause_browser_video()
            self.browser.hide()
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ffmpeg_exe = os.path.join(script_dir, 'ffmpeg', 'bin', 'ffmpeg.exe')
            
            base_url = f'https://www.youtube.com/watch?v={video_id}'
            ydl_opts = {
                'format': 'bestvideo[height<=?1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # Prefer MP4 video and M4A audio
                'merge_output_format': 'mp4',
                'quiet': False,
                'no_warnings': False,
                'logger': logging.getLogger(),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"Fetching video info for: {base_url}")
                info = ydl.extract_info(base_url, download=False)
                
                if not info:
                    print("Failed to get video info")
                    return

                # Check if this is a live stream
                is_live = info.get('is_live', False)
                print(f"Is live stream: {is_live}")

                # For live streams, prefer a single combined stream
                if is_live:
                    formats = info.get('formats', [])
                    formats = [f for f in formats if f.get('acodec', 'none') != 'none' 
                             and f.get('vcodec', 'none') != 'none']
                    
                    if formats:
                        formats.sort(key=lambda x: (x.get('height', 0), x.get('tbr', 0)), reverse=True)
                        best_format = formats[0]
                        video_url = best_format['url']
                        print(f"Using combined format for live: {best_format.get('format_note', '')}")
                        self.browser.hide()
                        self.video_player.show()
                        self.video_player.set_video_info(
                            title=f"🔴 LIVE: {info.get('title', '')}",
                            description=info.get('description', '')
                        )
                        self.video_player.play_video([video_url], base_url)
                        return

                # For VODs, use separate streams
                if 'requested_formats' in info:
                    formats = info['requested_formats']
                    video_format = None
                    audio_format = None
                    
                    for fmt in formats:
                        if fmt.get('vcodec', 'none') != 'none' and not video_format:
                            video_format = fmt
                            print(f"Video stream: {fmt.get('format_note', '')}, "
                                  f"Resolution: {fmt.get('height', '')}p, "
                                  f"Codec: {fmt.get('vcodec', '')}")
                        elif fmt.get('acodec', 'none') != 'none' and not audio_format:
                            audio_format = fmt
                            print(f"Audio stream: {fmt.get('format_note', '')}, "
                                  f"Codec: {fmt.get('acodec', '')}")

                    if video_format and audio_format:
                        self.browser.hide()
                        self.video_player.show()
                        self.video_player.set_video_info(
                            title=info.get('title', ''),
                            description=info.get('description', '')
                        )
                        self.video_player.play_video(
                            [video_format['url'], audio_format['url']], 
                            base_url
                        )
                    else:
                        # Fallback to best combined format
                        video_url = info['url']
                        print(f"Using combined format: {info.get('format_note', '')}")
                        self.browser.hide()
                        self.video_player.show()
                        self.video_player.set_video_info(
                            title=info.get('title', ''),
                            description=info.get('description', '')
                        )
                        self.video_player.play_video([video_url], base_url)

                # Fetch comments for VODs only
                if not is_live:
                    self.comment_fetcher = CommentFetcher(video_id)
                    self.comment_fetcher.comments_ready.connect(self.video_player.update_comments)
                    self.comment_fetcher.start(QThread.HighPriority)

        except Exception as e:
            print(f"Error playing video: {str(e)}")
            self.browser.show()

    def open_downloads_folder(self):
        """Open the downloads folder in custom file explorer"""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up one level to TYP folder
        downloads_dir = os.path.join(script_dir, 'downloads')
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
        dialog = FileExplorerDialog(downloads_dir, "Downloaded Videos", self)
        dialog.exec_()

    def open_audio_folder(self):
        """Open the mp3 folder in custom file explorer"""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up one level to TYP folder
        mp3_dir = os.path.join(script_dir, 'mp3')
        if not os.path.exists(mp3_dir):
            os.makedirs(mp3_dir)
        dialog = FileExplorerDialog(mp3_dir, "Downloaded Audio", self)
        dialog.exec_()

def main():
    # Add logging configuration
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    
    # Set application-wide icon for taskbar with correct path
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(script_dir, 'images', 'logo.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = YouTubeApp()
    window.show()
    sys.exit(app.exec_())
