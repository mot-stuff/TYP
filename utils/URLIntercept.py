from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
import re

class URLInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        # Check for video URLs more comprehensively
        if any(pattern in url for pattern in ['/watch?v=', 'youtu.be/']):
            # Only block media requests
            if info.resourceType() in [3, 4]:  # MediaResource = 3, XHR = 4
                info.block(True)
