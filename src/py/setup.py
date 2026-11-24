from pathlib import Path
import subprocess
import sys

PATH_REQUIREMENTS = "requirements.txt"

def main():
    # Get requirements.txt path
    requirements = Path(__file__).resolve().parent.parent.parent / PATH_REQUIREMENTS

    # Check pip is installed for this py interp
    pip_response = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True)

    # If pip is not installed, try to install it
    if pip_response.returncode != 0:
        try:
            subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=True)
        except subprocess.CalledProcessError:
            print(
                "Could not install pip\n " \
                "Install pip and try again",
                file=sys.stderr,
            )
            return 1

    # Install requirements in current env
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements)], check=True)
    except subprocess.CalledProcessError as error:
        print(f"Command failed with exit code {error.returncode}.", file=sys.stderr)
        return error.returncode or 1

    return 0

if __name__ == "__main__":
    raise SystemExit(main())