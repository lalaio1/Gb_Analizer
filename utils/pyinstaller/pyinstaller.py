from utils.pyinstaller.extractors.pyinstxtractor import PyInstArchive
from utils.pyinstaller.extractors.pyinstxtractorng import PyInstArchive as PyInstArchiveNG
from pystyle import Write, Colors
from typing import List


def ExtractPYInstaller(filename: str) -> PyInstArchive | PyInstArchiveNG:
    arch: PyInstArchive | PyInstArchiveNG = None
    try:
        arch = PyInstArchive(filename)
        if arch.open() and arch.checkFile() and arch.getCArchiveInfo():
            arch.parseTOC()
            arch.extractFiles()
            Write.Print('[+] Arquivo do PyInstaller extraído com sucesso: {0}\n'.format(filename), Colors.green_to_yellow, interval=0.0001)

    except:
        arch = PyInstArchiveNG(filename)
        if arch.open() and arch.checkFile() and arch.getCArchiveInfo():
            arch.parseTOC()
            arch.extractFiles()
            Write.Print(f'[+] Arquivo do PyInstaller extraído com sucesso: {filename}\n', Colors.green_to_yellow, interval=0.0001)

    finally:
        arch.close()
    return arch
