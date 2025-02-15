from PyQt5.QtWebEngineWidgets import QWebEnginePage

class CustomWebPage(QWebEnginePage):
    # This will allow the browser to play the video in the background while the custom player is playing the video in the foreground so algo gets updated
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.featurePermissionRequested.connect(self.handlePermissionRequest)

    def handlePermissionRequest(self, url, feature):
        self.setFeaturePermission(url, feature, QWebEnginePage.PermissionGrantedByUser)
