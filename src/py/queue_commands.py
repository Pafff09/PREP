# terminal_runner.py
import queue
import subprocess
import threading

class QueueJobs:
    def __init__(self, root, terminal, poll_ms=100):

        self.root = root
        self.terminal = terminal
        self.poll_ms = poll_ms

        self.jobs = queue.Queue()
        self.events = queue.Queue()
        self.process = None
        self.running = False
        self.closed = False
        self.poll_scheduled = False

    def add(self, command, label=""):
        
        if self.closed:
            return

        self.jobs.put((command, label))
        self._start_next()
        self._schedule_poll()

    def clear(self):
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.configure(state="disabled")

    def _start_next(self):
        if self.closed or self.running:
            return

        try:
            command, label = self.jobs.get_nowait()
        except queue.Empty:
            return

        self.running = True

        if label:
            self._write(f"\n Starting: {label}\n")

        threading.Thread(
            target=self._run_command,
            args=(command,),
            daemon=True,
        ).start()

    def _run_command(self, command):
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for line in self.process.stdout:
                self.events.put(("output", line))

            return_code = self.process.wait()
            self.events.put(("done", return_code))

        except Exception as error:
            self.events.put(("output", f"Could not run command: {error}\n"))
            self.events.put(("done", None))

        finally:
            self.process = None

    def _schedule_poll(self):
        if not self.closed and not self.poll_scheduled:
            self.poll_scheduled = True
            self.root.after(self.poll_ms, self._poll_events)

    def _poll_events(self):
        self.poll_scheduled = False

        try:
            while True:
                event, value = self.events.get_nowait()

                if event == "output":
                    self._write(value)

                elif event == "done":
                    status = "completed" if value == 0 else f"failed (exit code: {value})"
                    self._write(f"\nJob {status}.\n")
                    self.running = False
                    self._start_next()

        except queue.Empty:
            pass

        if self.running or not self.jobs.empty():
            self._schedule_poll()

    def _write(self, text):
        self.terminal.configure(state="normal")
        self.terminal.insert("end", text)
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def close(self):
        self.closed = True

        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
