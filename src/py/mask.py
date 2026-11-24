import os, subprocess, sys, queue, threading
from pathlib import Path

import cv2
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector

class AddMask:
    def __init__(self, parent, terminal):

        self.parent = parent
        self.terminal = terminal

        # Queueing jobs 
        self.output_queue = queue.Queue()
        self.pending_jobs = []
        self.mask_running = False
        self.output_polling = False

        self.input_dir = ""
        self.output_dir = ""
        self.ffmpeg_exe = ""
        self.files = []
        self.index = 0
        self.frame_inx = 0
        self.frame = None
        self.path = None

        self.user_operating_system = sys.platform

        if self.user_operating_system in ("linux", "linux2", "darwin"):
            self.mask_script = os.path.join("src", "sh", "mask.sh")
        elif self.user_operating_system == "win32":
            self.mask_script = os.path.join("src", "ps1", "mask.ps1")
        else:
            raise OSError(f"Unsupported operating system: {self.user_operating_system}")

        ### Create and set-up the figure ###
        self.fig = Figure(figsize=(7, 5))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_axis_off()
        self.ax.text(0.5, 0.5, "Load both input and output",
                    ha="center", va="center", transform=self.ax.transAxes)

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

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

        self.canvas.mpl_connect("key_press_event", self.on_key_press)

        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0

    def load_folder(self, input_dir, output_dir, ffmpeg_exe):

        # Paths
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.ffmpeg_exe = ffmpeg_exe

        # Get files
        self.files = sorted(
            (path.name for path in Path(input_dir).iterdir() if path.is_file()),
            key=str.casefold,
        )

        # Video and frame index
        self.index = 0
        self.frame_inx = 0

        if not self.files:
            self.ax.clear()
            self.ax.text(0.5, 0.5, "No files found", ha="center", va="center", transform=self.ax.transAxes)
            self.ax.set_axis_off()
            self.canvas.draw_idle()
            return

        return self.show_frame(self.index)

    def show_frame(self, index):
        self.index = index
        self.path = os.path.join(self.input_dir, self.files[index])

        capture = cv2.VideoCapture(self.path)
        capture.set(cv2.CAP_PROP_POS_FRAMES, self.frame_inx)
        success, frame = capture.read()
        capture.release()

        if not success or frame is None:
            self.ax.clear()
            self.ax.text(0.5, 0.5, f"Could not read a frame from:\n{self.files[index]}",
                        ha="center", va="center", transform=self.ax.transAxes)
            self.ax.set_axis_off()
            self.canvas.draw_idle()
            return

        self.frame = frame
        self.redraw()

    def redraw(self):
        self.ax.clear()

        if self.frame is not None:
            display_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            self.ax.imshow(display_frame)

        self.ax.set_title(
            f"{self.files[self.index]} — frame {self.frame_inx}"
        )
        self.ax.set_axis_off()
        self.canvas.draw_idle()

    def mask_current_video(self):

        if self.width <= 0 or self.height <= 0:
            return

        filename = os.path.splitext(self.files[self.index])[0]

        parameters = [
            self.ffmpeg_exe,
            self.path,
            str(self.x),
            str(self.y),
            str(self.width),
            str(self.height),
            self.output_dir,
            filename,
        ]

        if self.user_operating_system in ("linux", "linux2", "darwin"):
            command = ["sh", self.mask_script, *parameters]
        else:
            command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", 
                       "-File", self.mask_script, *parameters,]

        # Append the new command and either start it, or queue it
        self.pending_jobs.append((filename, command))
        self._start_next_mask_job()
        self._schedule_output_poll()

    ''' Queueing jobs methods '''

    def _start_next_mask_job(self):
        if self.mask_running or not self.pending_jobs:
            return

        filename, command = self.pending_jobs.pop(0)
        self.mask_running = True

        self.terminal.configure(state="normal")
        self.terminal.insert("end", f"\nStarting: {filename}\n")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

        threading.Thread(
            target=self._run_mask_command,
            args=(command,),
            daemon=True,
        ).start()

    def _schedule_output_poll(self):
        if not self.output_polling:
            self.output_polling = True
            self.parent.after(100, self._drain_output_queue)

    def _drain_output_queue(self):
        try:
            while True:
                event, value = self.output_queue.get_nowait()

                if event == "output":
                    self.terminal.configure(state="normal")
                    self.terminal.insert("end", value)
                    self.terminal.see("end")
                    self.terminal.configure(state="disabled")

                elif event == "done":
                    status = "completed" if value == 0 else f"failed (exit code: {value})"

                    self.terminal.configure(state="normal")
                    self.terminal.insert("end", f"\nJob {status}.\n")
                    self.terminal.see("end")
                    self.terminal.configure(state="disabled")

                    self.mask_running = False
                    self._start_next_mask_job()

        except queue.Empty:
            pass

        if self.mask_running or self.pending_jobs:
            self.parent.after(100, self._drain_output_queue)
        else:
            self.output_polling = False

    ''' Running jobs methods '''

    def _run_mask_command(self, command):
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for line in process.stdout:
                self.output_queue.put(("output", line))

            return_code = process.wait()
            self.output_queue.put(("done", return_code))

        except Exception as error:
            self.output_queue.put(("output", f"Error: {error}\n"))
        self.output_queue.put(("done", None))

    ''' Handle events in the PLT methods '''

    def on_select(self, start, end):
        if start.xdata is None or start.ydata is None:
            return
        if end.xdata is None or end.ydata is None:
            return

        self.x = int(min(start.xdata, end.xdata))
        self.y = int(min(start.ydata, end.ydata))
        self.width = int(abs(end.xdata - start.xdata))
        self.height = int(abs(end.ydata - start.ydata))

    def on_key_press(self, event):

        if event.key == "right":
            self.frame_inx += 1
            self.show_frame(self.index)
        elif event.key == "left":
            if self.frame_inx > 0:
                self.frame_inx -= 1
                self.show_frame(self.index)
        elif event.key == "enter":

            # If input, output or ffmpeg are missing - do not run 
            if not self.input_dir or not self.output_dir or not self.ffmpeg_exe:
                return

            # Else, run script
            self.mask_current_video()

            # Then move to next file, if it is not the last one in the directory
            if self.index < len(self.files) - 1:
                self.frame_inx = 0
                self.show_frame(self.index + 1)
            # If it is the last, clear ax
            else:
                self.frame = None
                self.ax.clear()
                self.ax.text(0.5, 0.5, f"No more files in {self.input_dir}", ha="center", va="center", transform=self.ax.transAxes)
                self.ax.set_axis_off()
                self.canvas.draw_idle()