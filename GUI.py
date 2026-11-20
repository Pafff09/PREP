import subprocess, threading, queue, json, sys, os
from pathlib import Path

from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
import tkinter as tk

### General paths ###$
PAHT_STORAGE = os.path.join("storage", "paths.json")

### Python Scripts ###
CONTRAST_SCRIPT = os.path.join("src", "py", "contrast.py")
CROP_SCRIPT = os.path.join("src", "py", "crop.py")
MASK_SCRIPT = os.path.join("src", "py", "mask.py")

# Get user's operating system
user_operating_system = sys.platform

### Bash/Zsh scripts for Linux and Mac ###
if user_operating_system in ["linux", "linux2", "darwin"]:
    CAP_FPS_SCRIPT = os.path.join("src", "sh", "cap_fps.sh")
    LETTER_BOX_SCRIPT = os.path.join("src", "sh", "letter_box.sh")
    TEST_SETTINGS_SCRIPT = os.path.join("src", "sh", "test_settings.sh")
### Powershell scripts for Windows ###
elif user_operating_system == "win32":
    CAP_FPS_SCRIPT = os.path.join("src", "ps1", "cap_fps.ps1")
    LETTER_BOX_SCRIPT = os.path.join("src", "ps1", "letter_box.ps1")
    TEST_SETTINGS_SCRIPT = os.path.join("src", "ps1", "test_settings.ps1")


class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly", iconphoto="assets/logo.png")

        # Window parameters
        self.title("PREP")
        self.geometry("1600x900")
        self.minsize(720, 520)

         # Read JSON file
        with open(PAHT_STORAGE, "r") as file:
            self.storage = json.load(file)

        # Home page
        self.ffmpeg_exe_path = tk.StringVar()

        # Check for existing variables in STORAGE
        if self.storage["path_ffmpeg"] != "":
            self.ffmpeg_exe_path.set(self.storage["path_ffmpeg"])
        
        # General parameters for repetitive pages
        self.pages = {}
        self.nav_buttons = {}
        self.run_buttons = []
        self.file_pages = {}

        # Threads parameters
        self.result_queue = queue.Queue()
        self.script_running = False

        # Cap FPS Parameters
        self.cap_input_dir = tk.StringVar()
        self.cap_output_dir = tk.StringVar()
        self.target_frames = tk.StringVar(value="25")

        # Leterbox Parameters
        self.letter_input_dir = tk.StringVar()
        self.letter_output_dir = tk.StringVar()
        self.letterbox_width = tk.StringVar(value="672")
        self.letterbox_height = tk.StringVar(value="672")

        # Build the layout and initialise the program in the "Home" page
        self._build_layout()
        self.show_page("Home")

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Top bar
        top_bar = ttk.Frame(self, padding=12)
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        ttk.Label(
            top_bar,
            text="Preprocess Recordings of Ethological Protocols",
            font=("TkDefaultFont", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(4, 20))

        button_bar = ttk.Frame(top_bar)
        button_bar.grid(row=0, column=1, sticky="e")

        page_names = ["Home", "Cap FPS", "Contrast", "Crop", "Mask", "Letter Box"]

        for name in page_names:
            button = ttk.Button(
                button_bar,
                text=name,
                bootstyle="secondary outline",
                command=lambda page=name: self.show_page(page),
            )
            button.pack(side="left", padx=4)
            self.nav_buttons[name] = button

        # Main page area
        self.page_area = ttk.Frame(self, padding=20)
        self.page_area.grid(row=1, column=0, sticky="nsew")
        self.page_area.grid_columnconfigure(0, weight=1)
        self.page_area.grid_rowconfigure(0, weight=1)

        self._build_home_page()
        self._build_cap_fps_page()
        self._build_folder_script_page("Contrast", CONTRAST_SCRIPT)
        self._build_folder_script_page("Crop", CROP_SCRIPT)
        self._build_folder_script_page("Mask", MASK_SCRIPT)
        self._build_letter_box_page()

    def _build_home_page(self):
        # Create/Config the Frame for the page
        page = ttk.Frame(self.page_area, padding=24)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(2, weight=1)
        self.pages["Home"] = page

        ttk.Label(page,
                  text="Default options for the program",
                  font=("TkDefaultFont", 16, "bold"),
                  wraplength=700
                  ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ### ffmpeg path ###
        self.ffmpeg_exe_label = ttk.Label(page,
                  text="FFMPEG path:"
                  ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(page,
                  textvariable=self.ffmpeg_exe_path
                  ).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Button(page,
                   text="Find...",
                   bootstyle="secondary",
                   command=self.chose_ffmpeg_path,
                    ).grid(row=1, column=2, padx=(8, 0), pady=6)
        if self.ffmpeg_exe_path.get().strip() != "":
            self.ffmpeg_exe_label.config(icon="check", bootstyle="success")
        
        self.pages["Home"] = page

    def _new_file_list(self, parent):
        """Create a file list with a vertical scrollbar."""
        frame = ttk.Frame(parent)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        tree = ttk.Treeview(
            frame,
            columns=("filename",),
            show="headings",
            height=10,
        )
        tree.heading("filename", text="Files in input folder")
        tree.column("filename", anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=tree.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)

        return frame, tree

    def _build_cap_fps_page(self):
        page = ttk.Frame(self.page_area, padding=24)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(2, weight=1)
        self.pages["Cap FPS"] = page

        ttk.Label(
            page,
            text="Cap FPS",
            font=("TkDefaultFont", 22, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ttk.Label(page, text="Input folder:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.cap_input_dir).grid(
            row=1, column=1, sticky="ew", pady=6
        )
        ttk.Button(
            page,
            text="Browse…",
            bootstyle="secondary",
            command=self.choose_cap_folder,
        ).grid(row=1, column=2, padx=(8, 0), pady=6)

        files_frame, self.cap_file_list = self._new_file_list(page)
        files_frame.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=(12, 16),
        )

        ttk.Label(page, text="Output directory:").grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.cap_output_dir).grid(
            row=3, column=1, sticky="ew", pady=6
        )
        ttk.Button(
            page,
            text="Browse…",
            bootstyle="secondary",
            command=lambda: self.choose_output_directory(
                self.cap_output_dir
            ),
        ).grid(row=3, column=2, padx=(8, 0), pady=6)

        ttk.Label(page, text="Desired frame count:").grid(
            row=4, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.target_frames, width=12).grid(
            row=4, column=1, sticky="w", pady=6
        )

        self.cap_status = ttk.Label(page, text="Ready")
        self.cap_status.grid(row=5, column=1, sticky="w", padx=10)

        run_button = ttk.Button(
            page,
            text="Run Cap FPS",
            bootstyle="success",
            command=self.run_cap_fps,
        )
        run_button.grid(row=5, column=0, sticky="w", pady=(16, 0))
        self.run_buttons.append(run_button)

    def _build_letter_box_page(self):
        page = ttk.Frame(self.page_area, padding=24)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(2, weight=1)
        self.pages["Letter Box"] = page

        ttk.Label(
            page,
            text="Letter Box",
            font=("TkDefaultFont", 22, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ttk.Label(page, text="Input folder:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.letter_input_dir).grid(
            row=1, column=1, sticky="ew", pady=6
        )
        ttk.Button(
            page,
            text="Browse…",
            bootstyle="secondary",
            command=lambda: self.choose_folder_for_page("Letter Box"),
        ).grid(row=1, column=2, padx=(8, 0), pady=6)

        files_frame, file_list = self._new_file_list(page)
        files_frame.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=(12, 16),
        )

        ttk.Label(page, text="Output directory:").grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.letter_output_dir).grid(
            row=3, column=1, sticky="ew", pady=6
        )
        ttk.Button(
            page,
            text="Browse…",
            bootstyle="secondary",
            command=lambda: self.choose_output_directory(self.letter_output_dir),
        ).grid(row=3, column=2, padx=(8, 0), pady=6)

        ### Width & Height ###
        ttk.Label(page, text="Letterbox Width:"
                  ).grid(row=4, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(page, textvariable=self.letterbox_width, width=12
                  ).grid(row=4, column=1, sticky="w", pady=6)

        ttk.Label(page, text="Letterbox Height:"
                  ).grid(row=5, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(page, textvariable=self.letterbox_height, width=12
                  ).grid(row=5, column=1, sticky="w", pady=6)

        self.letter_box_status = ttk.Label(page, text="Ready")
        self.letter_box_status.grid(row=6, column=1, sticky="w", padx=10)

        run_button = ttk.Button(
            page,
            text="Run Letterbox",
            bootstyle="success",
            command=self.run_letter_box,
        )
        run_button.grid(row=6, column=0, sticky="w", pady=(16, 0))
        self.run_buttons.append(run_button)

        # This is a dumb way to solve the problem; Solve later
        self.file_pages["Letter Box"] = {
            "input_dir": self.letter_input_dir,
            "output_dir": self.letter_output_dir,
            "file_list": file_list
        }

    def _build_folder_script_page(self, name, script_path):
        
        page = ttk.Frame(self.page_area, padding=24)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(2, weight=1)
        self.pages[name] = page

        input_dir = tk.StringVar()
        output_dir = tk.StringVar()

        ttk.Label(
            page,
            text=name,
            font=("TkDefaultFont", 22, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ttk.Label(page, text="Input folder:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=input_dir).grid(
            row=1, column=1, sticky="ew", pady=6
        )
        ttk.Button(
            page,
            text="Browse…",
            bootstyle="secondary",
            command=lambda n=name: self.choose_folder_for_page(n),
        ).grid(row=1, column=2, padx=(8, 0), pady=6)

        files_frame, file_list = self._new_file_list(page)
        files_frame.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=(12, 16),
        )

        ttk.Label(page, text="Output directory:").grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=output_dir).grid(
            row=3, column=1, sticky="ew", pady=6
        )
        ttk.Button(
            page,
            text="Browse…",
            bootstyle="secondary",
            command=lambda var=output_dir: self.choose_output_directory(var),
        ).grid(row=3, column=2, padx=(8, 0), pady=6)

        status = ttk.Label(page, text="Ready")
        status.grid(row=4, column=1, sticky="w", padx=10)

        run_button = ttk.Button(
            page,
            text=f"Run {name}",
            bootstyle="success",
            command=lambda n=name: self.run_folder_script(n),
        )
        run_button.grid(row=4, column=0, sticky="w", pady=(16, 0))
        self.run_buttons.append(run_button)

        self.file_pages[name] = {
            "input_dir": input_dir,
            "output_dir": output_dir,
            "file_list": file_list,
            "status": status,
            "script": script_path,
        }

    def show_page(self, page_name):
        self.pages[page_name].tkraise()

        for name, button in self.nav_buttons.items():
            style = "primary" if name == page_name else "secondary outline"
            button.configure(bootstyle=style)

    def _populate_file_list(self, tree, folder):
        tree.delete(*tree.get_children())

        try:
            files = sorted(
                path.name for path in Path(folder).iterdir() if path.is_file()
            )
        except OSError as error:
            messagebox.showerror("Folder error", str(error), parent=self)
            return

        for filename in files:
            tree.insert("", "end", values=(filename,))

        return len(files)

    def chose_ffmpeg_path(self):
        # Ask for the name of the ffmpeg file
        exe = filedialog.askopenfilename(title="Select ffmpeg.exe")

        # If nothing is selected, do not run the rest
        if not exe:
            return

        ### Test if ffmpeg path provided is functional ###
        # Linux and Mac #
        if user_operating_system in ["linux", "linux2", "darwin"]:
            command = ["sh", TEST_SETTINGS_SCRIPT, *[exe]]
        # Windows #
        elif user_operating_system in ["win32"]:
            command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", TEST_SETTINGS_SCRIPT, *[exe]]

        # Run the command
        response = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        check=False)

        # If errors,
        if response.returncode != 0:
            messagebox.showerror(
                "Invalid .exe",
                "The path provided does not act as bin/ffmpeg.exe",
                parent=self,
            )
            return
        
        # Set is as the entry value
        self.ffmpeg_exe_path.set(exe)

        # Change label to reflect it works
        self.ffmpeg_exe_label.config(icon="check", bootstyle="success")

        # Save to the JSON file for re-use
        with open(PAHT_STORAGE, 'w') as file:
            self.storage["path_ffmpeg"] = exe
            json.dump(self.storage, file, indent=2)

    def choose_cap_folder(self):
        folder = filedialog.askdirectory(title="Select Cap FPS input folder")
        if not folder:
            return

        self.cap_input_dir.set(folder)
        count = self._populate_file_list(self.cap_file_list, folder)

        if count is not None:
            self.cap_status.configure(text=f"{count} file(s) found")

    def choose_folder_for_page(self, page_name):
        folder = filedialog.askdirectory(
            title=f"Select {page_name} input folder"
        )
        if not folder:
            return

        page = self.file_pages[page_name]
        page["input_dir"].set(folder)
        self._populate_file_list(page["file_list"], folder)

    def choose_output_directory(self, variable):
        folder = filedialog.askdirectory(
            title="Choose output directory",
            mustexist=False,
        )
        if folder:
            variable.set(folder)

    def ensure_output_directory(self, directory):
        """Create the output directory if it doesn't exist."""
        path = Path(directory).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())

    def run_letter_box(self):
        page = self.file_pages["Letter Box"]
        input_dir = page["input_dir"].get().strip()
        output_dir = self.letter_output_dir.get().strip()

        width = self.letterbox_width.get().strip()
        height = self.letterbox_height.get().strip()

        try:
            if int(width) <= 0 or int(height) <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid size",
                "Width and Height should be a positive integer",
                parent=self,
            )
            return

        if not input_dir or not Path(input_dir).is_dir():
            messagebox.showerror(
                "Missing input",
                "Choose a valid input folder.",
                parent=self,
            )
            return

        if not output_dir:
            messagebox.showerror(
                "Missing output",
                "Choose an output directory.",
                parent=self,
            )
            return

        self.start_script(LETTER_BOX_SCRIPT, [self.storage["path_ffmpeg"], input_dir, output_dir, width, height], self.letter_box_status)

    def run_cap_fps(self):
        ffmpeg_exe = self.storage["path_ffmpeg"]
        input_dir = self.cap_input_dir.get().strip()
        output_dir = self.cap_output_dir.get().strip()

        try:
            frames = int(self.target_frames.get().strip())
            if frames <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid frame count",
                "Enter a positive whole number of frames.",
                parent=self,
            )
            return

        if not input_dir or not Path(input_dir).is_dir():
            messagebox.showerror(
                "Missing input",
                "Choose a valid input folder.",
                parent=self,
            )
            return

        if not output_dir:
            messagebox.showerror(
                "Missing output",
                "Choose an output directory.",
                parent=self,
            )
            return

        try:
            output_dir = self.ensure_output_directory(output_dir)
        except OSError as error:
            messagebox.showerror(
                "Output directory error", str(error), parent=self
            )
            return

        self.start_script(CAP_FPS_SCRIPT, [ffmpeg_exe, input_dir, str(frames), output_dir], self.cap_status)

    def run_folder_script(self, page_name):
        page = self.file_pages[page_name]
        input_dir = page["input_dir"].get().strip()
        output_dir = page["output_dir"].get().strip()

        if not input_dir or not Path(input_dir).is_dir():
            messagebox.showerror(
                "Missing input",
                "Choose a valid input folder.",
                parent=self,
            )
            return

        if not output_dir:
            messagebox.showerror(
                "Missing output",
                "Choose an output directory.",
                parent=self,
            )
            return

        try:
            output_dir = self.ensure_output_directory(output_dir)
        except OSError as error:
            messagebox.showerror(
                "Output directory error", str(error), parent=self
            )
            return

        self.start_script(page["script"], [input_dir, output_dir, self.storage["path_ffmpeg"]], page["status"])

    def start_script(self, script_path, arguments, status_label):
        if self.script_running:
            return

        # Run both bash and python scripts
        if ".sh" in script_path:
            command = ["sh", script_path, *arguments]
        elif ".ps1" in script_path:
            command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path, *arguments]
        elif ".py" in script_path:
            command = ["python", script_path, *arguments]

        # Change label in GUI for "Running"
        self.script_running = True
        self.active_status = status_label
        status_label.configure(text="Running…", bootstyle="default")

        # Disable the other tools whilst one process is running
        for button in self.run_buttons:
            button.configure(state="disabled")

        # Thread to background process
        threading.Thread(
            target=self._run_command,
            args=(command,),
            daemon=True,
        ).start()

        # Check if process has not failed
        self.after(100, self.check_script_result)

    def _run_command(self, command):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False)

            self.result_queue.put((result.returncode, result.stdout, result.stderr))

        except Exception as error:
            self.result_queue.put((None, "", str(error)))

    def check_script_result(self):
        
        try:
            # If code has returned something: finished or error -> Run the rest of the code
            return_code, stdout, stderr = self.result_queue.get_nowait()

        except queue.Empty:
            # If code is still running, continue
            self.after(100, self.check_script_result)
            return

        self.script_running = False

        for button in self.run_buttons:
            button.configure(state="normal")

        if return_code == 0:
            self.active_status.configure(text="Completed", bootstyle="success")
            messagebox.showinfo(
                "Script complete",
                stdout.strip() or "The script completed successfully.",
                parent=self,
            )
        else:
            self.active_status.configure(text="Failed", bootstyle="danger")
            messagebox.showerror(
                "Script failed",
                stderr.strip() or stdout.strip() or "The script failed.",
                parent=self,
            )

if __name__ == "__main__":
    app = App()
    app.mainloop()
