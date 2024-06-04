import sys
from cx_Freeze import setup, Executable
from pathlib import Path

# Replace 'your_script.py' with the name of your Python script.
executables = [Executable("eyelab\\main.py")]

# Add any other necessary options.
options = {
    'build_exe': {  
        'packages': [
            'qimage2ndarray', 'skimage', 'eyepy', 'requests', 'PySide6', 'numpy', 'matplotlib', 'fastrlock'
        ],
        'includes': [],
        'excludes': [],
        'include_msvcr': True if sys.platform == 'win32' else False,
    },
}

setup(
    name="Eyelab",
    version="0.4.2",
    description="Multi-modal annotation tool for eye imaging data",
    options=options,
    executables=executables
)
