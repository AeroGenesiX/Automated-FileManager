import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QSlider, QLabel, QStyle, QApplication
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl

logger = logging.getLogger("automgr.previews.video")

class VideoPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("VideoPreviewWidget initialized.")
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;") # Black background for video area
        
        self.play_button = QPushButton()
        self.play_button.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.setEnabled(False)
        self.play_button.setToolTip("Play/Pause")
        self.play_button.clicked.connect(self.toggle_play_pause)
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0,0)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.position_slider.setEnabled(False)
        # Only connect sliderPressed/sliderReleased if available (Qt >= 6.4)
        if hasattr(self.position_slider, 'sliderPressed'):
            self.position_slider.sliderPressed.connect(self._pause_on_slider)
        if hasattr(self.position_slider, 'sliderReleased'):
            self.position_slider.sliderReleased.connect(self._resume_on_slider)
        self._was_playing_before_slider = False

        self.duration_label = QLabel("--:-- / --:--")
        self.duration_label.setMinimumWidth(80) # To prevent layout jumps

        self.error_label = QLabel()
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("color: red;")

        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0,0,0,0)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.position_slider, 1) # Slider takes more space
        control_layout.addWidget(self.duration_label)


        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.video_widget, 1) # Video widget takes most space
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.error_label)
        self.error_label.hide()

        self.player.playbackStateChanged.connect(self.update_play_button_icon)
        self.player.positionChanged.connect(self.update_slider_position)
        self.player.durationChanged.connect(self.update_slider_range)
        self.player.errorOccurred.connect(self.handle_error)
        self.player.mediaStatusChanged.connect(self.handle_media_status)

        self.player.setVideoOutput(self.video_widget)

    def load_video(self, video_path):
        self.clear_preview() # Clear previous state
        logger.info(f"Loading video: {video_path}")
        self.player.setSource(QUrl.fromLocalFile(video_path))
        # Don't enable play button until media is loaded (see handle_media_status)
        # self.player.play() # Optionally auto-play

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            logger.debug("Video paused.")
        else:
            self.player.play()
            logger.debug("Video playing.")

    def update_play_button_icon(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.play_button.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
    def _format_time(self, ms):
        s = round(ms / 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:01d}:{m:02d}:{s:02d}"
        return f"{m:01d}:{s:02d}"

    def update_slider_position(self, position):
        self.position_slider.setValue(position)
        duration = self.player.duration()
        self.duration_label.setText(f"{self._format_time(position)} / {self._format_time(duration)}")


    def update_slider_range(self, duration):
        self.position_slider.setRange(0, duration)
        self.duration_label.setText(f"{self._format_time(0)} / {self._format_time(duration)}")


    def set_position(self, position):
        self.player.setPosition(position)
        
    def handle_media_status(self, status):
        logger.debug(f"Media status changed: {status}")
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            self.play_button.setEnabled(True)
            self.position_slider.setEnabled(True)
            self.error_label.hide()
            logger.info("Video media loaded successfully.")
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.play_button.setEnabled(False)
            self.position_slider.setEnabled(False)
            self.error_label.setText("Error: Invalid media or unsupported format.")
            self.error_label.show()
            logger.error("Invalid media or unsupported video format.")
        elif status == QMediaPlayer.MediaStatus.NoMedia:
             self.play_button.setEnabled(False)
             self.position_slider.setEnabled(False)
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            logger.info("Video reached end of media.")
            # self.player.setPosition(0) # Rewind or stop
            self.player.stop() # Stop to reset play button icon


    def handle_error(self, error: QMediaPlayer.Error):
        # This error signal is for playback errors, not necessarily load errors
        self.play_button.setEnabled(False) # Usually disable on error
        self.position_slider.setEnabled(False)
        error_string = self.player.errorString()
        if not error_string:
            error_map = {
                QMediaPlayer.Error.ResourceError: "Resource error (file not found or format issue).",
                QMediaPlayer.Error.ResourceError: "Resource error (file not found or format issue).",
                QMediaPlayer.Error.FormatError: "Format error (codec not supported or corrupted file).",
                QMediaPlayer.Error.NetworkError: "Network error.",
                QMediaPlayer.Error.AccessDeniedError: "Access denied."
            }
        
        self.error_label.setText(f"Playback Error: {error_string}")
        self.error_label.show()
        logger.error(f"Video Player Error: {error_string} (Code: {error})")

    def clear_preview(self):
        logger.debug("Clearing video preview.")
        if self.player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self.player.stop()
        self.player.setSource(QUrl())
        self.play_button.setEnabled(False)
        self.position_slider.setEnabled(False)
        self.position_slider.setValue(0)
        self.duration_label.setText("--:-- / --:--")
        self.error_label.hide()
        self._was_playing_before_slider = False
        # Force QVideoWidget to repaint to clear the last frame
        # This can be tricky. Sometimes it helps to hide/show or set a null source.
        self.video_widget.update()
        logger.debug("Video preview cleared.")


    def setVisible(self, visible):
        super().setVisible(visible)
        if not visible:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
                logger.debug("Video paused as preview widget became hidden.")
        # else:
            # Optionally resume if it was playing before being hidden
            # if self.player.mediaStatus() == QMediaPlayer.MediaStatus.LoadedMedia and \
            #    self._was_playing_before_hidden: # Need to track this state
            #     self.player.play()

    def _pause_on_slider(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self._was_playing_before_slider = True
        else:
            self._was_playing_before_slider = False

    def _resume_on_slider(self):
        if self._was_playing_before_slider:
            self.player.play()