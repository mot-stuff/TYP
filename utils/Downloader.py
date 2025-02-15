from PyQt5.QtCore import QThread, pyqtSignal
import os
import yt_dlp

class Downloader(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(float)

    def __init__(self, url, download_type='video'):
        super().__init__()
        self.url = url
        self.download_type = download_type
        self.ydl_opts = None

    def configure_download(self):
        # Get the TYP root directory (two levels up from utils)
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ffmpeg_path = os.path.join(script_dir, 'ffmpeg', 'bin', 'ffmpeg.exe')
        
        if not os.path.exists(ffmpeg_path):
            self.error.emit(f"FFmpeg not found at: {ffmpeg_path}")
            return False

        if self.download_type == 'video':
            # Use downloads directory in TYP root
            downloads_dir = os.path.join(script_dir, 'downloads')
            if not os.path.exists(downloads_dir):
                os.makedirs(downloads_dir)

            self.ydl_opts = {
                'ffmpeg_location': ffmpeg_path,
                'format': 'best',
                'outtmpl': os.path.join(downloads_dir, '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'writethumbnail': True,
                'keepvideo': True,
                'quiet': False,
                'verbose': True,
                'no_warnings': False,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            }
        else:  # mp3
            # Use mp3 directory in TYP root
            mp3_dir = os.path.join(script_dir, 'mp3')
            if not os.path.exists(mp3_dir):
                os.makedirs(mp3_dir)

            self.ydl_opts = {
                'ffmpeg_location': ffmpeg_path,
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(mp3_dir, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
                'quiet': False,
                'verbose': True,
                'no_warnings': False,
            }
        return True

    def run(self):
        try:
            if not self.configure_download():
                return

            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([self.url])
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
