import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector

import sys
import cv2
import os, subprocess

class addMaks:
    def __init__(self, input_dir, output_dir, ffmpeg_exe):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.ffmpeg_exe = ffmpeg_exe

        # Get user's operating system
        self.user_operating_system = sys.platform

        ### Bash/Zsh scripts for Linux and Mac ###
        if self.user_operating_system in ["linux", "linux2", "darwin"]:
            self.mask_script = os.path.join("src", "sh", "mask.sh")

        ### Powershell scripts for Windows ###
        elif self.user_operating_system == "win32":
            self.mask_script = os.path.join("src", "ps1", "mask.ps1")

        self.files = sorted(os.listdir(input_dir))
        if not self.files:
            raise ValueError(f"No files found in {input_dir!r}")

        self.index = 0
        self.frame = None
        self.path = None
        self.frame_inx = 0

        self.INSTRUCTION_WIDTH = 1
        self.INSTRUCTION_COLOR = (255, 0, 0)
        self.INSTRUCTION_SIZE = 0.5
        self.INSTRUCTION_FONT = cv2.FONT_HERSHEY_SIMPLEX
        self.INSTRUCTION_GAP = 30

        self.fig, self.ax = plt.subplots()
        self.fig.canvas.mpl_connect("key_press_event", self.on_key_press)

        self.selector = RectangleSelector(
                        self.ax,
                        self.on_select,
                        useblit=True,
                        button=[1],
                        minspanx=2,
                        minspany=2,
                        spancoords="pixels",
                        interactive=True,
                    )

    def show_frame(self, index):
        self.index = index
        self.path = os.path.join(self.input_dir, self.files[index])

        capture = cv2.VideoCapture(self.path)
        capture.set(cv2.CAP_PROP_POS_FRAMES, self.frame_inx)
        success, frame = capture.read()
        capture.release()

        if not success or frame is None:
            raise RuntimeError(f"Could not read an frame from {self.path!r}")

        self.frame = frame
        self.redraw()

    def mask_current_frame(self):

        filename = os.path.splitext(self.files[self.index])[0] 

        parameters = [self.ffmpeg_exe, self.path, str(self.x), str(self.y), str(self.width), str(self.height), self.output_dir, filename,]

        # Command for linux and mac
        if self.user_operating_system in ["linux", "linux2", "darwin"]:
            command = ["sh", self.mask_script, *parameters]

        # Command for windows
        elif self.user_operating_system in ["win32"]:
            command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", self.mask_script, *parameters]

        subprocess.run(command, check=False, capture_output=True, text=True)

    def on_key_press(self, event):
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

        if event.key != "enter":
            return

        self.mask_current_frame()

        if self.index >= len(self.files) - 1:
            plt.close(self.fig)
            return

        # Reset frame index before passing to the next
        self.frame_inx = 0
        self.show_frame(self.index + 1)

    def redraw(self):
        display_frame = self.frame

        instructions = [
            "Left-CLICK drag to select the area to mask",
            "LEFT-ARROW for the next frame",
            "RIGHT-ARROW for the previous frame",
            "Press ENTER to crop and continue",
            "Press ESCAPE to quit"]
        
        for pos, text in enumerate(instructions):
            cv2.putText(display_frame, text, (10, self.INSTRUCTION_GAP + pos * self.INSTRUCTION_GAP),
                        self.INSTRUCTION_FONT, self.INSTRUCTION_SIZE,
                        self.INSTRUCTION_COLOR, self.INSTRUCTION_WIDTH)

        self.ax.clear()
        self.ax.imshow(display_frame)
        self.ax.set_axis_off()
        self.fig.canvas.draw_idle()

    def on_select(self, start, end):
        if start.xdata is None or end.xdata is None:
            return

        self.x = int(start.xdata) + 1
        self.y = int(start.ydata) + 1
        self.width = int(abs(end.xdata - start.xdata))
        self.height = int(abs(end.ydata - start.ydata))

    def run(self):
        self.show_frame(self.index)
        plt.show()

if __name__ == "__main__":

    app = addMaks(sys.argv[1], sys.argv[2], sys.argv[3])
    app.run()
    