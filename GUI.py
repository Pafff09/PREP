# Libraries
import subprocess, threading, queue, json, sys, os
from pathlib import Path

# External libraries
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
import tkinter as tk
import cv2

# Python scripts
from src.py.crop import ContourCropper
from src.py.contrast import Contrast
from src.py.mask import AddMask

### General paths ###
PAHT_STORAGE = os.path.join("storage", "paths.json")
PATH_REQUIREMENTS = "requirements.txt"

### Python Scripts ###
CONTRAST_SCRIPT = os.path.join("src", "py", "contrast.py")
CROP_SCRIPT = os.path.join("src", "py", "crop.py")
MASK_SCRIPT = os.path.join("src", "py", "mask.py")
SETUP_SCRIPT = os.path.join("src", "py", "setup.py")

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

    ''' BUILD PAGES '''

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

        # Build the terminal
        self.terminal_frame, self.terminal = self._new_terminal(self.page_area)
        self.terminal_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(12, 16))

        self._build_home_page()
        self._build_cap_fps_page()
        self._build_contrast_page()
        self._build_crop_page()
        self._build_mask_page()
        self._build_letter_box_page()
    
    def _build_home_page(self):

        # Create/Config the Frame for the page
        page = ttk.Frame(self.page_area, padding=24)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(1, weight=1)
        self.pages["Home"] = page

        ttk.Label(page, text="Setting up PREP", font=("TkDefaultFont", 16, "bold"), wraplength=700
                  ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ### ffmpeg path ###
        self.ffmpeg_exe_label = ttk.Label(page, text="FFMPEG path::")
        self.ffmpeg_exe_label.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(page, textvariable=self.ffmpeg_exe_path
                    ).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Button(page, icon="folder", bootstyle="secondary",
                    command=lambda: self.chose_ffmpeg_path()
                    ).grid(row=1, column=2, padx=(8, 0), pady=6)

        # Check for existing ffmpeg path in storage and if it still functional
        if self.storage["path_ffmpeg"] != "":
            self.ffmpeg_exe_path.set(self.storage["path_ffmpeg"])
            if self.test_ffmpeg_path(self.storage["path_ffmpeg"]) == 0:
                self.ffmpeg_exe_label.config(icon="check", bootstyle="success")
            else:
                self.ffmpeg_exe_label.config(icon="file-earmark-excel", bootstyle="danger")

        ### set up ###
        self.command_install_dependencies = ttk.StringVar(value="pip install -r requirements.txt")
        self.dependencies_label =  ttk.Label(page, text="Install dependencies")
        self.dependencies_label.grid(row=2, column=0, columnspan=2, padx=(0, 0), pady=6, sticky="w")
        ttk.Entry(page, textvariable=self.command_install_dependencies,
                ).grid(row=2, column=1, sticky="ew", pady=6)
        ttk.Button(page, icon="download", bootstyle="secondary",
                    command=self.ensure_requirements,
                    ).grid(row=2, column=2, padx=(8, 0), pady=6)

         # Checking if libraries are installed in the current python version
        if self.test_requirements() == 1:
            self.dependencies_label.config(icon="exclamation-triangle", bootstyle="warning")
        else:
            self.dependencies_label.config(icon="check", bootstyle="success")
        
        self.pages["Home"] = page

        ### user configs (os, env) ###
        ttk.Label(page, text="User's configs", font=("TkDefaultFont", 14, "bold"),
                  ).grid(row=3, column=0, sticky="w", pady=(30, 0))
        ttk.Label(page, text=f"Detected user's OS            || {user_operating_system}"
                  ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Label(page, text=f"Detected user's virtualenv || {sys.prefix}"
                ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 10))

    def _build_cap_fps_page(self):

        # Add page main frame
        page = ttk.Frame(self.page_area, padding=24)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(2, weight=1)
        self.pages["Cap FPS"] = page

        # Title of the page
        ttk.Label(page, text="Cap FPS", font=("TkDefaultFont", 22, "bold")
                  ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        # Input directory
        ttk.Label(page, text="Input folder:"
                  ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(page, textvariable=self.cap_input_dir
                  ).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Button(page, icon="folder", bootstyle="secondary", command=self.choose_cap_folder
                   ).grid(row=1, column=2, padx=(8, 0), pady=6)

        # Tree viewer
        files_frame, self.cap_file_list = self._new_file_list(page)
        files_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(12, 16))

        # Output directory
        ttk.Label(page, text="Output directory:"
                  ).grid(row=4, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(page, textvariable=self.cap_output_dir
                  ).grid(row=4, column=1, sticky="ew", pady=6)
        ttk.Button(page, icon="folder", bootstyle="secondary",
                   command=lambda: self.choose_output_directory(self.cap_output_dir)
                  ).grid(row=4, column=2, padx=(8, 0), pady=6)

        # Desired FPS 
        ttk.Label(page, text="Desired frame count:"
                  ).grid(row=5, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(page, textvariable=self.target_frames, width=12
                  ).grid(row=5, column=1, sticky="w", pady=6)

        # Script status
        self.cap_status = ttk.Label(page, text="Ready")
        self.cap_status.grid(row=6, column=1, sticky="w", padx=10)

        # Run button
        run_button = ttk.Button(
            page,
            text="Run Cap FPS",
            bootstyle="success",
            command=self.run_cap_fps,
        )
        run_button.grid(row=6, column=0, sticky="w", pady=(16, 0))
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
        ttk.Button(page, icon="folder", bootstyle="secondary",
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
        ttk.Button(page, icon="folder", bootstyle="secondary",
                    command=lambda: self.choose_output_directory(self.letter_output_dir),
                  ).grid(row=3, column=2, padx=(8, 0), pady=6)

        ### Width & Height ###
        parameters_frame = ttk.Frame(page)
        parameters_frame.grid(row=4, column=0, columnspan=2, sticky="w", padx=(0, 10), pady=6)
        ttk.Label(parameters_frame, text="Width:"
                  ).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(parameters_frame, textvariable=self.letterbox_width, width=12
                  ).grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(parameters_frame, text="Height:"
                  ).grid(row=0, column=3, sticky="w", padx=(10, 10), pady=6)
        ttk.Entry(parameters_frame, textvariable=self.letterbox_height, width=12
                  ).grid(row=0, column=4, sticky="w", pady=6)

        self.letter_box_status = ttk.Label(page, text="Ready")
        self.letter_box_status.grid(row=5, column=1, sticky="w", padx=10)

        run_button = ttk.Button(
            page,
            text="Run Letterbox",
            bootstyle="success",
            command=self.run_letter_box,
        )
        run_button.grid(row=5, column=0, sticky="w", pady=(16, 0))
        self.run_buttons.append(run_button)

        # This is a dumb way to solve the problem; Solve later
        self.file_pages["Letter Box"] = {
            "input_dir": self.letter_input_dir,
            "output_dir": self.letter_output_dir,
            "file_list": file_list
        }

    def _build_contrast_page(self):

        page = ttk.Frame(self.page_area, padding=24)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=2)
        page.grid_columnconfigure(2, weight=0)
        page.grid_rowconfigure(2, weight=1)
        self.pages["Contrast"] = page

        self.contrast_input_dir = tk.StringVar()
        self.contrast_output_dir = tk.StringVar()

        ttk.Label(
            page,
            text="Contrast",
            font=("TkDefaultFont", 22, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ttk.Label(page, text="Input folder:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.contrast_input_dir).grid(
            row=1, column=1, sticky="ew", pady=6
        )
        ttk.Button(page, icon="folder", bootstyle="secondary",
                    command=self.choose_contrast_folder,
                  ).grid(row=1, column=2, padx=(8, 0), pady=6)

        files_frame, self.contrast_file_list = self._new_file_list(page)
        files_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=(0, 12),
            pady=(12, 16),
        )

        self.contrast_plot_frame = ttk.Frame(page)
        self.contrast_plot_frame.grid(
            row=2,
            column=1,
            columnspan=2,
            sticky="nsew",
            pady=(12, 16),
        )

        ttk.Label(page, text="Output directory:").grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.contrast_output_dir).grid(
            row=3, column=1, sticky="ew", pady=6
        )
        ttk.Button(page, icon="folder", bootstyle="secondary",
                    command=self.choose_contrast_output_folder,
                   ).grid(row=3, column=2, padx=(8, 0), pady=6)

        self.contrast_tool = Contrast(self.contrast_plot_frame, self.terminal)

    def _build_crop_page(self):

        page = ttk.Frame(self.page_area, padding=24)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=2)
        page.grid_columnconfigure(2, weight=0)
        page.grid_rowconfigure(2, weight=1)
        self.pages["Crop"] = page

        self.crop_input_dir = tk.StringVar()
        self.crop_output_dir = tk.StringVar()

        ttk.Label(
            page,
            text="Crop",
            font=("TkDefaultFont", 22, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ttk.Label(page, text="Input folder:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.crop_input_dir).grid(
            row=1, column=1, sticky="ew", pady=6
        )
        ttk.Button(page, icon="folder", bootstyle="secondary",
                    command=self.choose_crop_folder,
                  ).grid(row=1, column=2, padx=(8, 0), pady=6)

        files_frame, self.crop_file_list = self._new_file_list(page)
        files_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=(0, 12),
            pady=(12, 16),
        )

        self.crop_plot_frame = ttk.Frame(page)
        self.crop_plot_frame.grid(
            row=2,
            column=1,
            columnspan=2,
            sticky="nsew",
            pady=(12, 16),
        )
        self.crop_tool = ContourCropper(self.crop_plot_frame, self.terminal)

        ttk.Label(page, text="Output directory:").grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.crop_output_dir).grid(
            row=3, column=1, sticky="ew", pady=6
        )
        ttk.Button(page, icon="folder", bootstyle="secondary",
                    command=self.choose_crop_output_folder,
                  ).grid(row=3, column=2, padx=(8, 0), pady=6)

    def _build_mask_page(self):
        page = ttk.Frame(self.page_area, padding=24)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=2)
        page.grid_columnconfigure(2, weight=0)
        page.grid_rowconfigure(2, weight=1)
        self.pages["Mask"] = page

        self.mask_input_dir = tk.StringVar()
        self.mask_output_dir = tk.StringVar()

        ttk.Label(
            page,
            text="Mask",
            font=("TkDefaultFont", 22, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        # Input
        ttk.Label(page, text="Input folder:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.mask_input_dir).grid(
            row=1, column=1, sticky="ew", pady=6
        )
        ttk.Button(page, icon="folder", bootstyle="secondary",
                    command=self.choose_mask_folder,
                  ).grid(row=1, column=2, padx=(8, 0), pady=6)

        files_frame, self.mask_file_list = self._new_file_list(page)
        files_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=(0, 12),
            pady=(12, 16),
        )

        self.mask_plot_frame = ttk.Frame(page)
        self.mask_plot_frame.grid(
            row=2,
            column=1,
            columnspan=2,
            sticky="nsew",
            pady=(12, 16),
        )

        # Output
        ttk.Label(page, text="Output directory:").grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Entry(page, textvariable=self.mask_output_dir).grid(
            row=3, column=1, sticky="ew", pady=6
        )
        ttk.Button(page, icon="folder", bootstyle="secondary",
                    command=self.choose_mask_output_folder,
                   ).grid(row=3, column=2, padx=(8, 0), pady=6)

        self.mask_tool = AddMask(self.mask_plot_frame, self.terminal)

    def show_page(self, page_name):
        self.pages[page_name].tkraise()

        for name, button in self.nav_buttons.items():
            style = "primary" if name == page_name else "secondary outline"
            button.configure(bootstyle=style)

    ''' TREEVIEWER/TERMINAL METHODS '''

    def _new_terminal(self, parent):
        frame = ttk.Frame(parent)

        terminal = tk.Text(
            frame, height=10, wrap="word",
            bg="#0c0c0c", fg="#d4d4d4", insertbackground="#d4d4d4", selectbackground="#264f78", selectforeground="#ffffff",
            font=("Consolas", 5), relief="flat", borderwidth=0, padx=10, pady=8, state="normal")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=terminal.yview)
        terminal.insert("end", f"{os.getcwd()} >")
        terminal.configure(yscrollcommand=scrollbar.set, state="disable")

        terminal.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        return frame, terminal

    def _new_file_list(self, parent):

        # Create a frame
        frame = ttk.Frame(parent)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # Tree viewer to visualise selected files
        tree = ttk.Treeview(
            frame,
            columns=("filename",),
            show="headings",
            height=10,
        )
        tree.heading("filename", text="Add a folder")
        tree.column("filename", anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")

        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=tree.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)

        return frame, tree

    def _populate_file_list(self, tree, folder, which=None):
        
        # Intercalate colors in the rows
        tree.tag_configure("odd", background="#676767")
        tree.tag_configure("even", background="#343434")

        # Format the label of the size of the file
        def format_size(size_bytes):
            size = float(size_bytes)
            for unit in ("B", "KB", "MB", "GB", "TB"):
                if size < 1024 or unit == "TB":
                    return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
                size /= 1024

        # Delete previous tree
        tree.delete(*tree.get_children())

        # Estalish baseline columns, headings and col widths
        columns = ["name", "extension", "size"]
        headings = {
            "name": "File name",
            "extension": "Extension",
            "size": "Size",
        }
        widths = {"name": 280, "extension": 90, "size": 90}

        ### Specific columns for each page ###
        # If called in FPS cap
        if which == "fps":
            columns.append("fps")
            headings["fps"] = "FPS"
            widths["fps"] = 90

        # Configs the treeviewer
        tree.configure(columns=columns, show="headings")

        for column in columns:
            tree.heading(column, text=headings[column], anchor="w")
            tree.column(column, width=widths[column], anchor="w")

        try:
            files = sorted(
                (path for path in Path(folder).iterdir() if path.is_file()),
                key=lambda path: path.name.casefold(),
            )
        except OSError as error:
            messagebox.showerror("Folder error", str(error), parent=self)
            return 0

        for index, path in enumerate(files):
            extension = path.suffix.lower() or "—"
            size = format_size(path.stat().st_size)
            vals = [path.name, extension, size]

            ### Get specific page values ###
            if which == "fps":
                cap = cv2.VideoCapture(str(path))
                fps = cap.get(cv2.CAP_PROP_FPS)
                vals.append(round(fps, 2) if cap.isOpened() and fps > 0 else None)
                cap.release()

            # Add to tree
            tree.insert("", "end", values=vals, tags=("even" if index % 2 == 0 else "odd"))

        return len(files)

    ''' SETUP METHODS '''

    def test_ffmpeg_path(self, path):

        bin_path = os.path.abspath(os.path.dirname(path))

        ### Test if ffmpeg path provided is functional ###
        # Linux and Mac #
        if user_operating_system in ["linux", "linux2", "darwin"]:
            command = ["sh", TEST_SETTINGS_SCRIPT, *[bin_path]]
        # Windows #
        elif user_operating_system in ["win32"]:
            command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", TEST_SETTINGS_SCRIPT, *[bin_path]]

        # Run the command
        response = subprocess.run(command, capture_output=True, text=True, check=False)

        # If there is an error, return 1
        if "ffmpeg version" not in response.stdout:
            messagebox.showerror(
                "Invalid .exe",
                f"{path} does not act as ffmpeg.exe",
                parent=self,
                )
            return 1
        # Else return 0
        else:
            return 0

    def test_requirements(self):

        response = str(subprocess.run(["python", "-m", "pip", "list"], capture_output=True, check=False).stdout)

        with open(PATH_REQUIREMENTS, "r") as file:
            for line in file.readlines():

                # Omit version from check
                if "=" in line:
                    line = line[:line.index("=")]

                # If at least once libraries from the requirements is not installed: warning
                if line[:-1] not in response:
                    print(f"{line[:-1]} not installed")
                    return 1

        return 0

    def chose_ffmpeg_path(self):
        # Ask for the name of the ffmpeg file
        path_exe = filedialog.askopenfilename(title="Select ffmpeg.exe")

        # If nothing is selected, do not run the rest
        if not path_exe:
            return

        # Test ffmpeg path provided
        if self.test_ffmpeg_path(path_exe) == 1:
            return
        
        # Set is as the entry value
        self.ffmpeg_exe_path.set(path_exe)

        # Change label to reflect it works
        self.ffmpeg_exe_label.config(icon="check", bootstyle="success")

        # Save to the JSON file for re-use
        with open(PAHT_STORAGE, 'w') as file:
            self.storage["path_ffmpeg"] = path_exe
            json.dump(self.storage, file, indent=2)

    def ensure_requirements(self):
        response = subprocess.run(["python", SETUP_SCRIPT], capture_output=True, check=False)

        if response.returncode != 0:
            messagebox.showerror("Error" ,"Failed to install requirements", parent=self)
            return
        else:
            messagebox.showinfo("Success", "Requirements have been installed", parent=self)
            self.test_requirements()
            return 

    ''' INPUT DIRECTORY  '''
    def choose_cap_folder(self):

        # Open filedialog - ask for a directory
        folder = filedialog.askdirectory(title="Select Cap FPS input folder")

        # If nothing is selected, do nothing
        if not folder:
            return

        # Set the input file to the folder provided
        self.cap_input_dir.set(folder)

        # Populate tree viewer with the given files
        # And get the returned number of file to show number of files
        count = self._populate_file_list(self.cap_file_list, folder, which="fps")
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

    def choose_contrast_folder(self):
        folder = filedialog.askdirectory(title="Select Contrast input folder")
        if not folder:
            return

        self.contrast_input_dir.set(folder)
        self._populate_file_list(self.contrast_file_list, folder)
        self.load_external_python_scripts(self.contrast_input_dir, self.contrast_output_dir, self.contrast_tool)

    def choose_crop_folder(self):
        folder = filedialog.askdirectory(title="Select Crop input folder")
        if not folder:
            return

        self.crop_input_dir.set(folder)
        self._populate_file_list(self.crop_file_list, folder)
        self.load_external_python_scripts(self.crop_input_dir, self.crop_output_dir, self.crop_tool) 

    def choose_mask_folder(self):

        # Ask for input folder
        folder = filedialog.askdirectory(title="Select Mask input folder")
        if not folder:
            return

        self.mask_input_dir.set(folder)
        self._populate_file_list(self.mask_file_list, folder)
        self.load_external_python_scripts(self.mask_input_dir, self.mask_output_dir, self.mask_tool) 

    ''' OUTPUT DIRECTORY '''

    def choose_output_directory(self, variable):
        folder = filedialog.askdirectory(
            title="Choose output directory",
            mustexist=False,
        )
        if folder:
            variable.set(folder)
   
    def choose_mask_output_folder(self):
        folder = filedialog.askdirectory(
            title="Choose output directory",
            mustexist=False,
        )
        if not folder:
            return

        self.mask_output_dir.set(folder)
        self.load_external_python_scripts(self.mask_input_dir, self.mask_output_dir, self.mask_tool) 

    def choose_contrast_output_folder(self):

        folder = filedialog.askdirectory(
            title="Choose output directory",
            mustexist=False,
        )
        if not folder:
            return

        self.contrast_output_dir.set(folder)
        self.load_external_python_scripts(self.contrast_input_dir, self.contrast_output_dir, self.contrast_tool)

    def choose_crop_output_folder(self):
    
        folder = filedialog.askdirectory(
            title="Choose output directory",
            mustexist=False,
        )
        if not folder:
            return

        self.crop_output_dir.set(folder)
        self.load_external_python_scripts(self.crop_input_dir, self.crop_output_dir, self.crop_tool) 

    def ensure_output_directory(self, directory):
        """Create the output directory if it doesn't exist."""
        path = Path(directory).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())

    ''' RUN SCRIPTS '''

    def _is_script_valid_to_run(self, input_dir, output_dir):

        # Check if input as been set // and if it a is a dir
        if not input_dir or not Path(input_dir).is_dir():
            messagebox.showerror(
                "Missing input",
                "Choose a valid input folder.",
                parent=self,
            )
            return 1

        # Check for output directory 
        if not output_dir:
            messagebox.showerror(
                "Missing output",
                "Choose an output directory.",
                parent=self,
            )
            return 1

        # Check for FFMPEG
        if self.storage["path_ffmpeg"] == "":
            messagebox.showerror(
                "Missing FFMPEG",
                "Select FFMPEG exe file.",
                parent=self,
            )
            return 1

        return 0

    def run_letter_box(self):
        page = self.file_pages["Letter Box"]
        input_dir = page["input_dir"].get().strip()
        output_dir = self.letter_output_dir.get().strip()

        if self._is_script_valid_to_run(input_dir, output_dir) == 1:
            return

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

        self.start_script(LETTER_BOX_SCRIPT, [self.storage["path_ffmpeg"], input_dir, output_dir, width, height], self.letter_box_status)

    def run_cap_fps(self):
        ffmpeg_exe = self.storage["path_ffmpeg"]
        input_dir = self.cap_input_dir.get().strip()
        output_dir = self.cap_output_dir.get().strip()

        if self._is_script_valid_to_run(input_dir, output_dir) == 1:
            return

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

        self.start_script(CAP_FPS_SCRIPT, [ffmpeg_exe, input_dir, str(frames), output_dir], self.cap_status)

    def load_external_python_scripts(self, input, output, tool):
        input_dir = input.get().strip()
        output_dir = output.get().strip()
        
        if not input_dir or not Path(input_dir).is_dir() or not output_dir or self.storage["path_ffmpeg"] == "":
            return

        command = tool.load_folder(
            input_dir,
            output_dir,
            self.storage["path_ffmpeg"],
        )

    ''' General run scripts '''

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

        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.configure(state="disabled")

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
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.command_process = process

            for line in process.stdout:
                self.result_queue.put(("output", line))

            return_code = process.wait()
            self.result_queue.put(("done", return_code))

        except Exception as error:
            self.result_queue.put(("output", f"Error: {error}\n"))
            self.result_queue.put(("done", None))

    def check_script_result(self):
        try:
            while True:
                event = self.result_queue.get_nowait()

                if event[0] == "output":
                    self.terminal.configure(state="normal")
                    self.terminal.insert("end", event[1])
                    self.terminal.see("end")
                    self.terminal.configure(state="disabled")

                elif event[0] == "done":
                    return_code = event[1]
                    self.script_running = False

                    for button in self.run_buttons:
                        button.configure(state="normal")

                    if return_code == 0:
                        self.active_status.configure(text="Completed", bootstyle="success")
                    else:
                        self.active_status.configure(text="Failed", bootstyle="danger")

                    return

        except queue.Empty:
            pass

        self.after(100, self.check_script_result)

if __name__ == "__main__":
    app = App()
    app.mainloop()
