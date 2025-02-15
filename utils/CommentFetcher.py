from PyQt5.QtCore import QThread, pyqtSignal
import yt_dlp

class CommentFetcher(QThread):
    comments_ready = pyqtSignal(list)
    
    def __init__(self, video_id):
        super().__init__()
        self.video_id = video_id

    def run(self):
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': False,
                'getcomments': True,
                'max_comments': 50,
                'comment_sort': ['top'],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    f'https://www.youtube.com/watch?v={self.video_id}',
                    download=False
                )
                comments = info.get('comments', [])[:50] if info else []
                self.comments_ready.emit(comments)
        except Exception as e:
            print(f"Error fetching comments: {str(e)}")
            self.comments_ready.emit([])
