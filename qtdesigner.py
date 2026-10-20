import PySide6
import os
import subprocess

ruta_designer = os.path.join(os.path.dirname(PySide6.__file__), 'designer.exe')
subprocess.Popen([ruta_designer])