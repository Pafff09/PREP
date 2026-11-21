import subprocess, sys, os

import cv2
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider, TextBox
from matplotlib.patches import Rectangle

class ContourCropper:
    def __init__(self, input_dir, output_dir, ffmpeg_exe):
        # Paths
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.ffmpeg_exe = ffmpeg_exe

        # Get user's operating system
        self.user_operating_system = sys.platform

        ### Bash/Zsh scripts for Linux and Mac ###
        if self.user_operating_system in ["linux", "linux2", "darwin"]:
            self.crop_script = os.path.join("src", "sh", "crop.sh")

        ### Powershell scripts for Windows ###
        elif self.user_operating_system == "win32":
            self.crop_script = os.path.join("src", "ps1", "crop.ps1")

        # Files in Input directory
        self.files = sorted(os.listdir(input_dir))
        if not self.files:
            raise ValueError(f"No files found in {input_dir!r}")

        # Drawing and crop parameters
        self.NON_SELECTED_COLOR = (0, 255, 255)
        self.SELECTED_COLOR = (0, 255, 0)
        self.LINE_WIDTH = 3
        self.BUFFER_AREA = 25

        # For the option of manual cropping
        self.manual_boxes = {}
        self.next_manual_id = -1
        self.drawing_manual_box = False
        self.manual_drag_start = None
        self.manual_preview = None
        self.manual_label = "M"
        self.manual_preview_color = "red"

        # For Edge detection
        self.CANNY_THRESHOLD_1 = 10
        self.CANNY_THRESHOLD_2 = 200
        self.BINARY_THRESHOLD = 160

        # For instructions on the canva
        self.INSTRUCTION_WIDTH = 1
        self.INSTRUCTION_COLOR = (255, 0, 0)
        self.INSTRUCTION_SIZE = 0.8
        self.INSTRUCTION_GAP = 40
        self.INSTRUCTION_FONT = cv2.FONT_HERSHEY_SIMPLEX

        # For frame contours
        self.index = 0
        self.frame = None
        self.path = None
        self.frame_inx = 0
        self.contour_label = "C"
        self.contours = []
        self.selected = set()
        self.selected_coordinates = {}
        self.contour_inputs = {}
        self.contour_textboxes = {}
        self.textbox_axes = {}

        # Canva
        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        self.fig.subplots_adjust(left=0.28, right=0.72, top=0.95, bottom=0.05)

        # Cnava connections
        self.fig.canvas.mpl_connect("button_press_event", self.on_mouse_click)
        self.fig.canvas.mpl_connect("button_press_event", self.on_manual_box_press)
        self.fig.canvas.mpl_connect("motion_notify_event", self.on_manual_box_motion)
        self.fig.canvas.mpl_connect("button_release_event", self.on_manual_box_release)
        self.fig.canvas.mpl_connect("key_press_event", self.on_key_press)


        # Sliders (Axes, Widget, Label rot & Update func)
        c1_ax = self.fig.add_axes([0.17, 0.25, 0.0225, 0.5])
        c2_ax = self.fig.add_axes([0.14, 0.25, 0.0225, 0.5])

        self.c1_slider = Slider(c1_ax, "Canny thresh 1", 0, 255, valinit=self.CANNY_THRESHOLD_1, orientation="vertical")
        self.c2_slider = Slider(c2_ax, "Canny thresh 2", 0, 255, valinit=self.CANNY_THRESHOLD_2, orientation="vertical",)

        self.c1_slider.label.set_rotation(90)
        self.c2_slider.label.set_rotation(90)

        self.c1_slider.on_changed(self.update_sliders)
        self.c2_slider.on_changed(self.update_sliders)

    def start_manual_box(self):
        self.drawing_manual_box = True
        self.manual_drag_start = None
        self.fig.canvas.draw_idle()

    def add_manual_box(self, x0, y0, x1, y1):

        # Get height and width from the manual box
        height, width = self.frame.shape[:2]

        # Get coordinates of the box
        left = max(0, min(width - 1, int(min(x0, x1))))
        top = max(0, min(height - 1, int(min(y0, y1))))
        right = max(0, min(width, int(max(x0, x1))))
        bottom = max(0, min(height, int(max(y0, y1))))

        # Avoid coordinate errors
        if right <= left or bottom <= top:
            return

        # Attribute an id in the negatives to not conflict with the contours
        manual_id = self.next_manual_id
        self.next_manual_id -= 1

        # Add the manual box to the selected box
        self.manual_boxes[manual_id] = (left, top, right, bottom)
        self.selected.add(manual_id)
        self.contour_inputs[manual_id] = ""

        # Add a textbox ax allwoing to rename
        textbox_ax = self.fig.add_axes([0.75, 0.85, 0.23, 0.05])
        textbox = TextBox(textbox_ax, f"{self.manual_label} {-manual_id}", initial="")
        textbox.on_text_change(lambda text, i=manual_id: self.save_contour_text(i, text))
        self.textbox_axes[manual_id] = textbox_ax
        self.contour_textboxes[manual_id] = textbox
        self.layout_textboxes()

        # Redraw the canva
        self.redraw()

    def on_manual_box_press(self, event):

        if not self.drawing_manual_box or event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return
        if event.button != 1:
            return

        self.manual_drag_start = (event.xdata, event.ydata)
        self.manual_preview = Rectangle(self.manual_drag_start, 0, 0, fill=False, edgecolor=self.manual_preview_color, linewidth=2)
        self.ax.add_patch(self.manual_preview)
        self.fig.canvas.draw_idle()

    def on_manual_box_motion(self, event):

        if self.manual_drag_start is None or self.manual_preview is None:
            return
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return

        x0, y0 = self.manual_drag_start
        self.manual_preview.set_xy((min(x0, event.xdata), min(y0, event.ydata)))
        self.manual_preview.set_width(abs(event.xdata - x0))
        self.manual_preview.set_height(abs(event.ydata - y0))
        self.fig.canvas.draw_idle()

    def on_manual_box_release(self, event):   

        if self.manual_drag_start is None:
            return

        start = self.manual_drag_start
        self.manual_drag_start = None

        if self.manual_preview is not None:
            self.manual_preview.remove()
            self.manual_preview = None

        if event.inaxes == self.ax and event.xdata is not None and event.ydata is not None:
            self.add_manual_box(*start, event.xdata, event.ydata)
        else:
            self.redraw()

    def find_contours(self):
        edges = cv2.Canny(
            self.blurred_frame,
            self.CANNY_THRESHOLD_1,
            self.CANNY_THRESHOLD_2,
            L2gradient=True,
        )

        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_LIST,  # includes contours inside other contours
            cv2.CHAIN_APPROX_SIMPLE,
        )

        return contours

    def add_contour_textbox(self, contour_index):
        if contour_index in self.contour_textboxes:
            return

        self.contour_inputs[contour_index] = ""

        textbox_ax = self.fig.add_axes([0.75, 0.85, 0.23, 0.05])
        textbox = TextBox(textbox_ax,f"{self.contour_label} {contour_index}", initial="")

        textbox.on_text_change(lambda text, i=contour_index: self.save_contour_text(i, text))

        self.textbox_axes[contour_index] = textbox_ax
        self.contour_textboxes[contour_index] = textbox
        self.layout_textboxes()

    def save_contour_text(self, contour_index, text):
        self.contour_inputs[contour_index] = text

    def remove_contour_textbox(self, contour_index):
        self.contour_textboxes.pop(contour_index, None)
        textbox_ax = self.textbox_axes.pop(contour_index, None)

        if textbox_ax is not None:
            textbox_ax.remove()

        self.contour_inputs.pop(contour_index, None)
        self.layout_textboxes()

    def layout_textboxes(self):

        count = len(self.textbox_axes)
        row_spacing = 0.55
        textbox_height = 0.32
        figure_height = max(6.0, 1.0 + count * row_spacing)

        self.fig.set_size_inches(12, figure_height, forward=True)

        slider_bottom = (figure_height - 3.0) / (2.0 * figure_height)
        for slider in (self.c1_slider, self.c2_slider):
            pos = slider.ax.get_position()
            slider.ax.set_position([pos.x0, slider_bottom, pos.width, 3.0 / figure_height])

        for row, item_id in enumerate(sorted(self.textbox_axes)):
            y = 1.0 - (0.45 + (row + 1) * row_spacing) / figure_height
            self.textbox_axes[item_id].set_position([0.75, y, 0.23, textbox_height / figure_height])

        self.fig.canvas.draw_idle()

    def show_frame(self, index):
        self.index = index
        self.path = os.path.join(self.input_dir, self.files[index])

        # Get the desired frame
        capture = cv2.VideoCapture(self.path)
        capture.set(cv2.CAP_PROP_POS_FRAMES, self.frame_inx)
        success, frame = capture.read()
        capture.release()

        if not success or frame is None:
            raise RuntimeError(f"Could not read an frame from {self.path!r}")

        # Textboxes and selections belong to the previous frame.
        for contour_index in list(self.contour_textboxes):
            self.remove_contour_textbox(contour_index)

        # Apply the contour algo to blurred/gray/frame
        self.frame = frame
        self.gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.blurred_frame = cv2.medianBlur(self.gray_frame, 5)
        self.contours = self.find_contours()

        self.selected.clear()
        self.selected_coordinates.clear()
        self.manual_boxes.clear()
        self.drawing_manual_box = False
        self.manual_drag_start = None

        if self.manual_preview is not None:
            self.manual_preview.remove()
            self.manual_preview = None

        self.redraw()

    def get_crop_coordinates(self):
        height, width = self.frame.shape[:2]
        coordinates = dict()

        for contour_index in self.selected:
            if contour_index in self.manual_boxes:
                continue

            x, y, box_width, box_height = cv2.boundingRect(
                self.contours[contour_index]
            )

            left = self.BUFFER_AREA // 2
            top = self.BUFFER_AREA // 2
            right = self.BUFFER_AREA - left
            bottom = self.BUFFER_AREA - top

            x0 = max(0, x - left)
            y0 = max(0, y - top)
            x1 = min(width, x + box_width + right)
            y1 = min(height, y + box_height + bottom)

            coordinates[contour_index] = f"({x0}, {y0}, {x1 - x0}, {y1 - y0})"

        # For manual boxes
        for manual_id in self.selected:
            if manual_id not in self.manual_boxes:
                continue

            x0, y0, x1, y1 = self.manual_boxes[manual_id]
            half_buffer = self.BUFFER_AREA // 2

            left = max(0, x0 - half_buffer)
            top = max(0, y0 - half_buffer)
            right = min(width, x1 + half_buffer)
            bottom = min(height, y1 + half_buffer)

            coordinates[manual_id] = (f"({left}, {top}, {right - left}, {bottom - top})")

        return coordinates

    def redraw(self):
        # Draw on a copy so repeated redraws do not alter the source frame.
        display_frame = self.frame.copy()
        self.selected_coordinates = self.get_crop_coordinates()

        for contour_index, contour in enumerate(self.contours):
            # Skip manual contours
            if contour_index in self.manual_boxes:
                continue

            color = (self.SELECTED_COLOR if contour_index in self.selected else self.NON_SELECTED_COLOR)
            cv2.drawContours(
                display_frame,
                [contour],
                -1,
                color,
                self.LINE_WIDTH,
            )

            if contour_index in self.selected:
                x, y, width, height = cv2.boundingRect(contour)
                x0 = max(0, x - self.BUFFER_AREA // 2)
                y0 = max(0, y - self.BUFFER_AREA // 2)
                x1 = min(self.frame.shape[1], x + width + self.BUFFER_AREA // 2)
                y1 = min(self.frame.shape[0], y + height + self.BUFFER_AREA // 2)

                cv2.rectangle(display_frame, (x0, y0), (x1, y1), self.SELECTED_COLOR,2)

                cv2.putText(display_frame, f"C {contour_index}", (int(x0+(width/2)), int(y0+(height/2))),
                            self.INSTRUCTION_FONT, 1, self.SELECTED_COLOR, self.LINE_WIDTH)

        # Draw the manual boxes
        for manual_id, (x0, y0, x1, y1) in self.manual_boxes.items():
            cv2.rectangle(display_frame, (x0, y0), (x1, y1), self.SELECTED_COLOR, 2)
            cv2.putText(display_frame, f"{self.manual_label} {-manual_id}", (x0 + (x1-x0)//2, y0 + (y1-y0)//2),
                self.INSTRUCTION_FONT, 1, self.SELECTED_COLOR, self.LINE_WIDTH)

        # Instructtion to add to the canva
        instructions = [
            "Left-CLICK to select contours to crop",
            "Right-CLICK to deselect contours",
            "LEFT-ARROW for the next frame",
            "RIGHT-ARROW for the previous frame",
            "Press B to toggle Manual mode",
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
        self.ax.imshow(display_frame)
        # If Manual is toggle, set title to refelct it
        if self.drawing_manual_box:
            self.ax.set_title("Manual mode: Drag your mouse to create the bounding box")
        self.ax.set_axis_off()
        self.fig.canvas.draw_idle()

    def nearest_contour(self, x, y):
        if not self.contours:
            return None

        point = np.array([x, y])
        distances = [
            np.min(np.sum((contour[:, 0, :] - point) ** 2, axis=1))
            for contour in self.contours
        ]
        return int(np.argmin(distances))

    def on_mouse_click(self, event):
        if self.drawing_manual_box:
            return
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        if event.button not in (1, 3):
            return

        px, py = event.xdata, event.ydata

        # Manual boxes take priority when the click is inside one
        for manual_id, (x0, y0, x1, y1) in list(self.manual_boxes.items()):
            if x0 <= px <= x1 and y0 <= py <= y1:
                if event.button == 1:
                    self.selected.add(manual_id)
                else:
                    self.selected.discard(manual_id)
                    self.manual_boxes.pop(manual_id)
                    self.remove_contour_textbox(manual_id)
                self.redraw()
                return

        contour_id = self.nearest_contour(px, py)
        if contour_id is None:
            return

        if event.button == 1:
            if contour_id not in self.selected:
                self.selected.add(contour_id)
                self.add_contour_textbox(contour_id)
        elif contour_id in self.selected:
            self.selected.remove(contour_id)
            self.remove_contour_textbox(contour_id)

        self.redraw()

    def update_sliders(self, _):
        self.CANNY_THRESHOLD_1 = int(self.c1_slider.val)
        self.CANNY_THRESHOLD_2 = int(self.c2_slider.val)

        # Recompute contours from the already-loaded frame; don't reopen the video
        self.contours = self.find_contours()

        # Remove the texbox from the contour only
        for item_id in list(self.contour_textboxes):
            if item_id not in self.manual_boxes:
                self.remove_contour_textbox(item_id)

        self.selected = {
            box_id for box_id in self.selected
            if box_id in self.manual_boxes
        }

        self.redraw()

    def crop_current_frame(self):
        filenames = self.contour_inputs
        coordinates = {key:self.selected_coordinates[key] for key in filenames.keys()}

        filenames = "/".join(filenames.values())
        coordinates = "/".join(coordinates.values())

        parameters = [self.ffmpeg_exe, self.path, coordinates, self.output_dir, filenames]

        # Command for linux and mac
        if self.user_operating_system in ["linux", "linux2", "darwin"]:
            command = ["sh", self.crop_script, *parameters]

        # Command for windows
        elif self.user_operating_system in ["win32"]:
            command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", self.crop_script, *parameters]

        subprocess.run(command, check=False)

    def on_key_press(self, event):
        # ESCAPE: close the window
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

        # B: Toggle Manual mode
        if event.key.lower() == "b":
            self.drawing_manual_box = not self.drawing_manual_box
            self.manual_drag_start = None

            if self.manual_preview is not None:
                self.manual_preview.remove()
                self.manual_preview = None

            self.redraw()
            return

        # Else: return the func earlier
        if event.key != "enter":
            return

        # Run the cropping script
        self.crop_current_frame()

        # If it is the last frame, close the canva
        if self.index >= len(self.files) - 1:
            plt.close(self.fig)
            return
        # Else, show next frame
        self.show_frame(self.index + 1)

    def run(self):
        self.show_frame(self.index)
        plt.show()

if __name__ == "__main__":
    app = ContourCropper(sys.argv[1], sys.argv[2], sys.argv[3])
    app.run()
