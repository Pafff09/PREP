import sys
import os
import ntpath
import subprocess

import cv2
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider

class ContourCropper:
    def __init__(self, input_dir, output_dir, ffmpeg_exe):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.ffmpeg_exe = ffmpeg_exe

        # Get user's operating system
        self.user_operating_system = sys.platform

        ### Bash/Zsh scripts for Linux and Mac ###
        if self.user_operating_system in ["linux", "linux2", "darwin"]:
            self.contrast_script = os.path.join("src", "sh", "contrast.sh")

        ### Powershell scripts for Windows ###
        elif self.user_operating_system == "win32":
            self.contrast_script = os.path.join("src", "ps1", "contrast.ps1")

        self.files = sorted(os.listdir(input_dir))
        if not self.files:
            raise ValueError(f"No files found in {input_dir!r}")

        self.BRIGHTNESS = 0
        self.CONTRAST = 0

        self.INSTRUCTION_WIDTH = 1
        self.INSTRUCTION_COLOR = (0, 0, 255)
        self.INSTRUCTION_SIZE = 0.8
        self.INSTRUCTION_GAP = 40
        self.INSTRUCTION_FONT = cv2.FONT_HERSHEY_SIMPLEX

        self.index = 0
        self.frame = None
        self.path = None
        self.frame_inx = 0

        # To set the inital slides with the real values of the first video
        self.show_frame(0, redraw=False)

        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        self.fig.subplots_adjust(left=0.28, right=0.72, top=0.95, bottom=0.05)

        self.fig.canvas.mpl_connect("key_press_event", self.on_key_press)

        # Sliders
        bright_ax = self.fig.add_axes([0.17, 0.25, 0.0225, 0.5])
        contra_ax = self.fig.add_axes([0.14, 0.25, 0.0225, 0.5])

        self.bright_slider = Slider(
            ax=bright_ax,
            label="BRIGHTNESS",
            valmin=0,
            valmax=255,
            valinit=self.BRIGHTNESS,
            orientation="vertical",
        )
        self.contra_slider = Slider(
            ax=contra_ax,
            label="CONTRAST",
            valmin=0,
            valmax=255,
            valinit=self.CONTRAST,
            orientation="vertical",
        )

        self.bright_slider.label.set_rotation(90)
        self.contra_slider.label.set_rotation(90)

        self.bright_slider.on_changed(self.update_sliders)
        self.contra_slider.on_changed(self.update_sliders)

    def show_frame(self, index, redraw=True):

        self.index = index
        self.path = os.path.join(self.input_dir, self.files[index])

        capture = cv2.VideoCapture(self.path)
        capture.set(cv2.CAP_PROP_POS_FRAMES, self.frame_inx)
        success, frame = capture.read()
        capture.release()

        if not success or frame is None:
            raise RuntimeError(f"Could not read an image/frame from {self.path!r}")

        if redraw == True:
            self.frame = frame
            self.redraw()
        else:
            initial_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.BRIGHTNESS = float(np.mean(initial_gray))
            self.CONTRAST = float(np.std(initial_gray))

    def ffmpeg_eq_filter(self):
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        current_mean = float(np.mean(gray))
        current_std = float(np.std(gray))

        # The contrast multiplier needed to reach the slider's target contrast.
        ff_contrast = self.CONTRAST / current_std if current_std > 0 else 1.0

        # Convert the target mean to FFmpeg's brightness offset.
        ff_brightness = (
            self.BRIGHTNESS
            - ff_contrast * current_mean
            - 127.5 * (1.0 - ff_contrast)
        ) / 255.0

        # Keep values within FFmpeg eq's documented ranges.
        ff_brightness = float(np.clip(ff_brightness, -1.0, 1.0))
        ff_contrast = float(np.clip(ff_contrast, -1000.0, 1000.0))

        return (ff_brightness, ff_contrast)

    def redraw(self):
        # Measure the unmodified frame.
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        current_mean = float(np.mean(gray))
        current_std = float(np.std(gray))

        if current_std > 0:
            alpha = self.CONTRAST / current_std
        else:
            alpha = 1.0

        beta = self.BRIGHTNESS - alpha * current_mean
        display_frame = np.clip(
            self.frame.astype(np.float32) * alpha + beta,
            0,
            255,
        ).astype(np.uint8)

        instructions = [
            "LEFT-ARROW for the next frame",
            "RIGHT-ARROW for the previous frame",
            "Press ENTER to crop and continue",
            "Press ESCAPE to quit",
        ]

        for pos, text in enumerate(instructions):
            cv2.putText(
                display_frame,
                text,
                (10, 40 + pos * self.INSTRUCTION_GAP),
                self.INSTRUCTION_FONT,
                self.INSTRUCTION_SIZE,
                self.INSTRUCTION_COLOR,
                self.INSTRUCTION_WIDTH,
            )

        self.ax.clear()
        self.ax.imshow(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
        self.ax.set_title(self.path)
        self.ax.set_axis_off()
        self.fig.canvas.draw_idle()

    def update_sliders(self, _):

        self.BRIGHTNESS = self.bright_slider.val
        self.CONTRAST = self.contra_slider.val

        if self.frame is not None:
            self.redraw()

    def run_script(self):

        # Get file name
        name = ntpath.basename(self.path)
        if "." in name:
            for i in range(name.count(".")):
                name = name[:-name[::-1].index(".")-1]

        eqVals = self.ffmpeg_eq_filter()

        parameters = [self.ffmpeg_exe, self.path, name, self.output_dir, str(eqVals[0]), str(eqVals[1])]

        # Command for linux and mac
        if self.user_operating_system in ["linux", "linux2", "darwin"]:
            command = ["sh", self.contrast_script, *parameters]

        # Command for windows
        elif self.user_operating_system in ["win32"]:
            command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", self.contrast_script, *parameters]

        subprocess.run(command, check=False)

    def on_key_press(self, event):

        # ESCAPE - brute force close the plt
        if event.key == "escape":
            plt.close(self.fig)
            return

        ### Allow the user to move inbetween frames of the same video ###
        # RIGHT ARROW - next frame
        if event.key == "right":
            self.frame_inx += 1
            self.show_frame(self.index)
        # LEFT ARROW - previous frame
        if event.key == "left":
            if self.frame_inx > 0:
                self.frame_inx -= 1
                self.show_frame(self.index)

        # OTHER - do nothing
        if event.key != "enter":
            return

        self.run_script()

        if self.index >= len(self.files) - 1:
            plt.close(self.fig)
            return

        self.frame_inx = 0
        self.show_frame(self.index + 1)

    def run(self):
        self.show_frame(self.index)
        plt.show()

if __name__ == "__main__":
    app = ContourCropper(sys.argv[1], sys.argv[2], sys.argv[3])
    app.run()
