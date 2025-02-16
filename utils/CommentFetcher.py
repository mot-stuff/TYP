from PyQt5.QtCore import QThread, pyqtSignal
import yt_dlp

class CommentFetcher(QThread):
    comments_ready = pyqtSignal(list)
    
    def __init__(self, video_id):
        super().__init__()
        self.video_id = video_id

    def run(self):
        import subprocess, json
        try:
            # Build the command with JSON dump and comments
            cmd = [
                "yt-dlp",
                "--write-comments",
                "--dump-single-json",
                f"https://www.youtube.com/watch?v={self.video_id}"
            ]
            output = subprocess.check_output(cmd, text=True)
            info = json.loads(output)
            comments = info.get('comments', [])
            # Ensure each comment has a like_count and author_thumbnail field
            default_thumb = "https://via.placeholder.com/40"
            for comment in comments:
                if 'like_count' not in comment:
                    comment['like_count'] = 0
                if not comment.get('author_thumbnail'):
                    comment['author_thumbnail'] = default_thumb
            # Sort comments by like_count in descending order and take top 50
            comments = sorted(comments, key=lambda x: x['like_count'], reverse=True)[:100]
            # Print JSON of comments for debugging
            self.comments_ready.emit(comments)
        except Exception as e:
            print(f"Error fetching comments: {str(e)}")
            self.comments_ready.emit([])
