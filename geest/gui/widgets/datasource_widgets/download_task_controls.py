# -*- coding: utf-8 -*-
"""Reusable download button controls with spinner and lifecycle states."""

from qgis.PyQt.QtCore import QSize, Qt, QTimer
from qgis.PyQt.QtGui import QMovie
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from geest.utilities import resources_path


class DownloadTaskControls:
    """Encapsulate common download button + spinner behavior for datasource widgets."""

    def __init__(self, button_text: str, tooltip: str, click_handler):
        """Create reusable controls and wire click callback.

        Args:
            button_text: Default button text.
            tooltip: Default button tooltip.
            click_handler: Callback invoked on button click.
        """
        self.default_text = button_text
        self.default_tooltip = tooltip
        self.default_style = "padding: 5px 10px;"

        self.container = QWidget()
        self.container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.button = QPushButton(self.default_text)
        self.button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.button.setToolTip(self.default_tooltip)
        self.button.setStyleSheet(self.default_style)
        self.button.clicked.connect(click_handler)

        self.spinner_label = QLabel()
        self.spinner_movie = QMovie(resources_path("resources", "throbber.gif"))
        self.spinner_movie.setScaledSize(QSize(24, 24))
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_label.setVisible(False)
        self.spinner_label.setAlignment(Qt.AlignVCenter)

        layout.addWidget(self.button)
        layout.addWidget(self.spinner_label)
        layout.addStretch()

    def set_running(self) -> None:
        """Set button to downloading state and show spinner."""
        self._set_state(
            text="Downloading...",
            enabled=False,
            style=self.default_style,
            tooltip=self.default_tooltip,
        )
        self.spinner_label.setVisible(True)
        self.spinner_movie.start()

    def update_progress(self, message: str) -> None:
        """Update button text based on task progress message."""
        if "Processing" in message:
            self.button.setText("Processing...")
        elif "complete" in message.lower():
            self.button.setText("Complete!")

    def set_downloaded(self, reset_after_ms: int = 2000) -> None:
        """Set successful completion state and auto-reset."""
        self._set_state(
            text="Downloaded!",
            enabled=True,
            style="background-color: #ccffcc; padding: 5px 10px;",
            tooltip=self.default_tooltip,
            stop_spinner=True,
        )
        QTimer.singleShot(reset_after_ms, self.reset)

    def set_download_failed(self, error_message: str) -> None:
        """Set standard failed state with retry tooltip."""
        self._set_state(
            text="Download Failed!",
            enabled=True,
            style="background-color: #ffcccc; padding: 5px 10px;",
            tooltip=f"Error: {error_message}\n\nClick to retry.",
            stop_spinner=True,
        )

    def set_error(self, error_message: str) -> None:
        """Set startup/runtime error state."""
        self._set_state(
            text="Error!",
            enabled=True,
            style="background-color: #ffcccc; padding: 5px 10px;",
            tooltip=f"Error: {error_message}",
            stop_spinner=True,
        )

    def set_not_found(self, path: str) -> None:
        """Set missing-output state."""
        self._set_state(
            text="Not Found!",
            enabled=True,
            style="background-color: #ffcccc; padding: 5px 10px;",
            tooltip=f"Error: Output file not found: {path}",
            stop_spinner=True,
        )

    def set_load_failed(self, path: str) -> None:
        """Set invalid-output load failure state."""
        self._set_state(
            text="Load Failed!",
            enabled=True,
            style="background-color: #ffcccc; padding: 5px 10px;",
            tooltip=f"Error: Could not load output layer: {path}",
            stop_spinner=True,
        )

    def set_cancelled(self) -> None:
        """Set cancelled state."""
        self._set_state(
            text="Cancelled",
            enabled=True,
            style="background-color: #ffffcc; padding: 5px 10px;",
            tooltip="Download was cancelled. Click to retry.",
            stop_spinner=True,
        )

    def stop_spinner(self) -> None:
        """Stop spinner animation and hide indicator."""
        self.spinner_movie.stop()
        self.spinner_label.setVisible(False)

    def reset(self) -> None:
        """Reset button to initial state."""
        self._set_state(
            text=self.default_text,
            enabled=True,
            style=self.default_style,
            tooltip=self.default_tooltip,
            stop_spinner=True,
        )

    def _set_state(
        self,
        text: str,
        enabled: bool,
        style: str,
        tooltip: str,
        stop_spinner: bool = False,
    ) -> None:
        """Apply a full UI state for the button controls."""
        self.button.setText(text)
        self.button.setEnabled(enabled)
        self.button.setStyleSheet(style)
        self.button.setToolTip(tooltip)
        if stop_spinner:
            self.stop_spinner()
