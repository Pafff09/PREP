import ntpath
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import ttkbootstrap as ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.py.queue_commands import QueueJobs

class Contrast:
    def __init__(self, parent, terminal):
        
        self.parent = parent
        self.terminal = terminal

        # Queueing jobs 
        self.contrast_queue = QueueJobs(self.parent, terminal)

        self.input_dir = ""
        self.output_dir = ""
        self.ffmpeg_exe = ""
        self.files = []
        self.index = 0
        self.frame = None
        self.path = None
        self.frame_inx = 0
        self.image_artist = None

        self.user_operating_system = sys.platform
        if self.user_operating_system in ("linux", "linux2", "darwin"):
            self.contrast_script = os.path.join("src", "sh", "contrast.sh")
        elif self.user_operating_system == "win32":
            self.contrast_script = os.path.join("src", "ps1", "contrast.ps1")
        else:
            raise OSError(
                f"Unsupported operating system: {self.user_operating_system}"
            )

        self.brightness_var = ttk.DoubleVar(value=0)
        self.contrast_var = ttk.DoubleVar(value=0)

        controls = ttk.Frame(parent, padding=(8, 0))
        controls.pack(side="right", fill="y")

        ttk.Label(controls, text="Brightness").pack(pady=(8, 0))
        self.brightness_scale = ttk.Scale(
            controls,
            from_=0,
            to=255,
            orient="vertical",
            variable=self.brightness_var,
            command=self.update_sliders,
            length=220,
        )
        self.brightness_scale.pack(fill="y", expand=True, padx=12)

        ttk.Label(controls, text="Contrast").pack(pady=(8, 0))
        self.contrast_scale = ttk.Scale(
            controls,
            from_=0,
            to=255,
            orient="vertical",
            variable=self.contrast_var,
            command=self.update_sliders,
            length=220,
        )
        self.contrast_scale.pack(fill="y", expand=True, padx=12)

        self.fig = Figure(figsize=(8, 5))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_axis_off()
        self.ax.text(0.5, 0.5, "Load both input and output",
                    ha="center", va="center", transform=self.ax.transAxes)

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(side="left", fill="both", expand=True)
        self.canvas.mpl_connect("key_press_event", self.on_key_press)

        self.BRIGHTNESS = 0.0
        self.CONTRAST = 0.0

    def load_folder(self, input_dir, output_dir, ffmpeg_exe):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.ffmpeg_exe = ffmpeg_exe
        self.files = sorted(
            (path.name for path in Path(input_dir).iterdir() if path.is_file()),
            key=str.casefold,
        )
        self.index = 0
        self.frame_inx = 0

        if not self.files:
            self.show_message("No files found")
            return

        self.show_frame(0, redraw=False)

    def show_message(self, text):
        self.frame = None
        self.ax.clear()
        self.ax.text(
            0.5,
            0.5,
            text,
            ha="center",
            va="center",
            transform=self.ax.transAxes,
        )
        self.ax.set_axis_off()
        self.canvas.draw_idle()

    def show_frame(self, index, redraw=True):
        self.index = index
        self.path = os.path.join(self.input_dir, self.files[index])

        capture = cv2.VideoCapture(self.path)
        capture.set(cv2.CAP_PROP_POS_FRAMES, self.frame_inx)
        success, frame = capture.read()
        capture.release()

        if not success or frame is None:
            self.show_message(f"Could not read a frame from:\n{self.path}")
            return

        self.frame = frame

        if not redraw:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.BRIGHTNESS = float(np.mean(gray))
            self.CONTRAST = float(np.std(gray))

            # Set the controls to this frame's initial brightness and contrast.
            self.brightness_var.set(self.BRIGHTNESS)
            self.contrast_var.set(self.CONTRAST)

        self.redraw()

    def ffmpeg_eq_filter(self):
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        current_mean = float(np.mean(gray))
        current_std = float(np.std(gray))

        ff_contrast = self.CONTRAST / current_std if current_std > 0 else 1.0
        ff_brightness = (
            self.BRIGHTNESS
            - ff_contrast * current_mean
            - 127.5 * (1.0 - ff_contrast)
        ) / 255.0

        ff_brightness = float(np.clip(ff_brightness, -1.0, 1.0))
        ff_contrast = float(np.clip(ff_contrast, -1000.0, 1000.0))

        return ff_brightness, ff_contrast

    def redraw(self):
        if self.frame is None:
            return

        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        current_mean = float(np.mean(gray))
        current_std = float(np.std(gray))

        alpha = self.CONTRAST / current_std if current_std > 0 else 1.0
        beta = self.BRIGHTNESS - alpha * current_mean

        display_frame = np.clip(
            self.frame.astype(np.float32) * alpha + beta,
            0,
            255,
        ).astype(np.uint8)

        display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

        self.ax.clear()
        self.ax.imshow(display_frame)
        self.ax.set_title(
            f"{self.path}\nFrame {self.frame_inx}"
        )
        self.ax.set_axis_off()
        self.canvas.draw_idle()

    def update_sliders(self, _value=None):
        self.BRIGHTNESS = float(self.brightness_var.get())
        self.CONTRAST = float(self.contrast_var.get())
        self.redraw()

    def run_script(self):
        name = ntpath.basename(self.path)
        name = os.path.splitext(name)[0]

        eq_values = self.ffmpeg_eq_filter()
        parameters = [self.ffmpeg_exe, self.path, name, self.output_dir,
                      str(eq_values[0]), str(eq_values[1])]

        filename = os.path.splitext(self.files[self.index])[0]

        if self.user_operating_system in ("linux", "linux2", "darwin"):
            command = ["sh", self.contrast_script, *parameters]
        else:
            command = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                self.contrast_script,
                *parameters,
            ]

        # Append the new command and either start it, or queue it
        self.contrast_queue.add(command, label=filename)

    def on_key_press(self, event):

        if event.key == "right":
            self.frame_inx += 1
            self.show_frame(self.index)
            return

        if event.key == "left":
            if self.frame_inx > 0:
                self.frame_inx -= 1
                self.show_frame(self.index)
            return

        if event.key != "enter":
            return

        self.run_script()

        if self.index < len(self.files) - 1:
            self.frame_inx = 0
            self.show_frame(self.index + 1)

        else:
            self.frame = None
            self.ax.clear()
            self.ax.text(0.5, 0.5, f"No more files in {self.input_dir}\n Wait for the queued files to be processed", ha="center", va="center", transform=self.ax.transAxes)
            self.ax.set_axis_off()
            self.canvas.draw_idle()