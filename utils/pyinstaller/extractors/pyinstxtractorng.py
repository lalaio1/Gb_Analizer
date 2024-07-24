import os
import sys
import zlib
import struct
import argparse

from uuid import uuid4 as uniquename

from Crypto.Cipher import AES
from Crypto.Util import Counter

from xdis.unmarshal import load_code
from utils.pyinstaller.pyinstallerExceptions import ExtractionError

from pystyle import Write, Colors


def pycHeader2Magic(header):
    header = bytearray(header)
    magicNumber = bytearray(header[:2])
    return magicNumber[1] << 8 | magicNumber[0]


class CTOCEntry:
    def __init__(
        self, position, cmprsdDataSize, uncmprsdDataSize, cmprsFlag, typeCmprsData, name
    ):
        self.position = position
        self.cmprsdDataSize = cmprsdDataSize
        self.uncmprsdDataSize = uncmprsdDataSize
        self.cmprsFlag = cmprsFlag
        self.typeCmprsData = typeCmprsData
        self.name = name


class PyInstArchive:
    PYINST20_COOKIE_SIZE = 24
    PYINST21_COOKIE_SIZE = 24 + 64 
    MAGIC = b"MEI\014\013\012\013\016"  

    def __init__(self, path):
        self.pymin = None
        self.pymaj = None
        self.pyinstVer = None
        self.filePath = path
        self.pycMagic = b"\0" * 4
        self.barePycList = [] 
        self.cryptoKey = None
        self.cryptoKeyFileData = None
        self.entrypoints = []

    def open(self):
        try:
            self.fPtr = open(self.filePath, "rb")
            self.fileSize = os.stat(self.filePath).st_size
        except:
            ExtractionError("[!] Error: Could not open {0}\n".format(self.filePath))
            return False
        return True

    def close(self):
        try:
            self.fPtr.close()
        except:
            pass

    def checkFile(self):
        Write.Print("[+] Processando {0}\n".format(self.filePath), Colors.green_to_yellow, interval=0.0001)


        searchChunkSize = 8192
        endPos = self.fileSize
        self.cookiePos = -1

        if endPos < len(self.MAGIC):
            ExtractionError("[!] Error : File is too short or truncated")
            return False

        while True:
            startPos = endPos - searchChunkSize if endPos >= searchChunkSize else 0
            chunkSize = endPos - startPos

            if chunkSize < len(self.MAGIC):
                break

            self.fPtr.seek(startPos, os.SEEK_SET)
            data = self.fPtr.read(chunkSize)

            offs = data.rfind(self.MAGIC)

            if offs != -1:
                self.cookiePos = startPos + offs
                break

            endPos = startPos + len(self.MAGIC) - 1

            if startPos == 0:
                break

        if self.cookiePos == -1:
            ExtractionError("[!] Error : Missing cookie, unsupported pyinstaller version or not a pyinstaller archive")
            return False

        self.fPtr.seek(self.cookiePos + self.PYINST20_COOKIE_SIZE, os.SEEK_SET)

        if b"python" in self.fPtr.read(64).lower():
            Write.Print("[+] Versão do PyInstaller: 2.1+\n", Colors.green_to_cyan, interval=0.0001)

            self.pyinstVer = 21  # pyinstaller 2.1+
        else:
            self.pyinstVer = 20  # pyinstaller 2.0
            Write.Print("[+] Versão do PyInstaller: 2.0\n", Colors.green_to_cyan, interval=0.0001)


        return True

    def getCArchiveInfo(self):
        try:
            if self.pyinstVer == 20:
                self.fPtr.seek(self.cookiePos, os.SEEK_SET)

                (magic, lengthofPackage, toc, tocLen, pyver) = struct.unpack(
                    "!8siiii", self.fPtr.read(self.PYINST20_COOKIE_SIZE)
                )

            elif self.pyinstVer == 21:
                self.fPtr.seek(self.cookiePos, os.SEEK_SET)

                (magic, lengthofPackage, toc, tocLen, pyver, pylibname) = struct.unpack(
                    "!8sIIii64s", self.fPtr.read(self.PYINST21_COOKIE_SIZE)
                )

        except:
            ExtractionError("[!] Error : The file is not a pyinstaller archive")
            return False

        self.pymaj, self.pymin = (
            (pyver // 100, pyver % 100) if pyver >= 100 else (pyver // 10, pyver % 10)
        )
        print("[+] Python version: {0}.{1}\n".format(self.pymaj, self.pymin))

        tailBytes = (
            self.fileSize
            - self.cookiePos
            - (
                self.PYINST20_COOKIE_SIZE
                if self.pyinstVer == 20
                else self.PYINST21_COOKIE_SIZE
            )
        )

        self.overlaySize = lengthofPackage + tailBytes
        self.overlayPos = self.fileSize - self.overlaySize
        self.tableOfContentsPos = self.overlayPos + toc
        self.tableOfContentsSize = tocLen

        Write.Print("[+] Comprimento do pacote: {0} bytes\n".format(lengthofPackage), Colors.green_to_cyan, interval=0.0001)

        return True

    def parseTOC(self):
        self.fPtr.seek(self.tableOfContentsPos, os.SEEK_SET)

        self.tocList = []
        parsedLen = 0

        while parsedLen < self.tableOfContentsSize:
            (entrySize,) = struct.unpack("!i", self.fPtr.read(4))
            nameLen = struct.calcsize("!iIIIBc")

            (
                entryPos,
                cmprsdDataSize,
                uncmprsdDataSize,
                cmprsFlag,
                typeCmprsData,
                name,
            ) = struct.unpack(
                "!IIIBc{0}s".format(entrySize - nameLen), self.fPtr.read(entrySize - 4)
            )

            try:
                name = name.decode("utf-8").rstrip("\0")
            except UnicodeDecodeError:
                newName = str(uniquename())
                Write.Print('[!] Aviso: O nome do arquivo {0} contém bytes inválidos. \n[!] Usando nome aleatório {1}\n'.format(name, newName), Colors.yellow_to_orange, interval=0.0001)

                name = newName

            if name.startswith("/"):
                name = name.lstrip("/")

            if len(name) == 0:
                name = str(uniquename())
                Write.Print("[!] Aviso: Encontrado um arquivo sem nome no CArchive. Usando nome aleatório {0}\n".format(name), Colors.yellow_to_orange, interval=0.0001)


            self.tocList.append(
                CTOCEntry(
                    self.overlayPos + entryPos,
                    cmprsdDataSize,
                    uncmprsdDataSize,
                    cmprsFlag,
                    typeCmprsData,
                    name,
                )
            )

            parsedLen += entrySize
        Write.Print("[+] Encontrado(s) {0} arquivo(s) no CArchive\n".format(len(self.tocList)), Colors.green_to_lightgreen, interval=0.0001)


    def _writeRawData(self, filepath, data):
        nm = (
            filepath.replace("\\", os.path.sep)
            .replace("/", os.path.sep)
            .replace("..", "__")
        )
        nmDir = os.path.dirname(nm)
        if nmDir != "" and not os.path.exists(
            nmDir
        ):
            os.makedirs(nmDir)

        with open(nm, "wb") as f:
            f.write(data)

    def extractFiles(self, one_dir):
        Write.Print("[+] Iniciando a extração...por favor, aguarde\n", Colors.blue_to_green, interval=0.0001)

        extractionDir = os.path.join(
            os.getcwd(), os.path.basename(self.filePath) + "_extracted"
        )

        if not os.path.exists(extractionDir):
            os.mkdir(extractionDir)

        os.chdir(extractionDir)

        for entry in self.tocList:
            self.fPtr.seek(entry.position, os.SEEK_SET)
            data = self.fPtr.read(entry.cmprsdDataSize)

            if entry.cmprsFlag == 1:
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    continue
                assert len(data) == entry.uncmprsdDataSize  

            if entry.typeCmprsData == b"d" or entry.typeCmprsData == b"o":
                continue

            basePath = os.path.dirname(entry.name)
            if basePath != "":
                if not os.path.exists(basePath):
                    os.makedirs(basePath)

            if entry.typeCmprsData == b"s":
                Write.Print("[+] Ponto de entrada possível: {0}.pyc\n".format(entry.name), Colors.green_to_blue, interval=0.0001)

                self.entrypoints.append(entry.name + ".pyc")

                if self.pycMagic == b"\0" * 4:
                    self.barePycList.append(entry.name + ".pyc")
                self._writePyc(entry.name + ".pyc", data)

            elif entry.typeCmprsData == b"M" or entry.typeCmprsData == b"m":
                if data[2:4] == b"\r\n":
                   
                    if self.pycMagic == b"\0" * 4:
                        self.pycMagic = data[0:4]
                    self._writeRawData(entry.name + ".pyc", data)

                    if entry.name.endswith("_crypto_key"):
                        Write.Print("[+] Arquivo _crypto_key detectado, salvando chave para descriptografia automática.\n", Colors.green_to_blue, interval=0.0001)

                        self.cryptoKeyFileData = self._extractCryptoKeyObject(data)

                else:
            
                    if self.pycMagic == b"\0" * 4:
                        self.barePycList.append(entry.name + ".pyc")

                    self._writePyc(entry.name + ".pyc", data)

                    if entry.name.endswith("_crypto_key"):
                        Write.Print("[+] Arquivo _crypto_key detectado, salvando chave para criptografia automática.\n", Colors.green_to_blue, interval=0.0001)

                        self.cryptoKeyFileData = data

            else:
                self._writeRawData(entry.name, data)

                if entry.typeCmprsData == b"z" or entry.typeCmprsData == b"Z":
                    self._extractPyz(entry.name, one_dir)

        self._fixBarePycs()

    def _fixBarePycs(self):
        for pycFile in self.barePycList:
            with open(pycFile, "r+b") as pycFile:
                pycFile.write(self.pycMagic)

    def _extractCryptoKeyObject(self, data):
        if self.pymaj >= 3 and self.pymin >= 7:
            return data[16:]
        elif self.pymaj >= 3 and self.pymin >= 3:
            return data[12:]
        else:
            return data[8:]

    def _writePyc(self, filename, data):
        with open(filename, "wb") as pycFile:
            pycFile.write(self.pycMagic)

            if self.pymaj >= 3 and self.pymin >= 7:  
                pycFile.write(b"\0" * 4) 
                pycFile.write(b"\0" * 8)  

            else:
                pycFile.write(b"\0" * 4) 
                if self.pymaj >= 3 and self.pymin >= 3:
                    pycFile.write(b"\0" * 4)  

            pycFile.write(data)

    def _getCryptoKey(self):
        if self.cryptoKey:
            return self.cryptoKey

        if not self.cryptoKeyFileData:
            return None

        co = load_code(self.cryptoKeyFileData, pycHeader2Magic(self.pycMagic))
        self.cryptoKey = co.co_consts[0]
        return self.cryptoKey

    def _tryDecrypt(self, ct, aes_mode):
        CRYPT_BLOCK_SIZE = 16

        key = bytes(self._getCryptoKey(), "utf-8")
        assert len(key) == 16

        iv = ct[:CRYPT_BLOCK_SIZE]

        if aes_mode == "ctr":
            ctr = Counter.new(128, initial_value=int.from_bytes(iv, byteorder="big"))
            cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
            return cipher.decrypt(ct[CRYPT_BLOCK_SIZE:])

        elif aes_mode == "cfb":
            cipher = AES.new(key, AES.MODE_CFB, iv)
            return cipher.decrypt(ct[CRYPT_BLOCK_SIZE:])            

    def _extractPyz(self, name, one_dir):
        if one_dir == True:
            dirName = "."
        else:
            dirName = name + "_extracted"
            if not os.path.exists(dirName):
                os.mkdir(dirName)

        with open(name, "rb") as f:
            pyzMagic = f.read(4)
            assert pyzMagic == b"PYZ\0"  

            pyzPycMagic = f.read(4) 

            if self.pycMagic == b"\0" * 4:
                self.pycMagic = pyzPycMagic

            elif self.pycMagic != pyzPycMagic:
                self.pycMagic = pyzPycMagic
                Write.Print("[!] Aviso: A mágica pyc dos arquivos dentro do arquivo PYZ é diferente daquela no CArchive.\n", Colors.yellow_to_red, interval=0.0001)


            (tocPosition,) = struct.unpack("!i", f.read(4))
            f.seek(tocPosition, os.SEEK_SET)

            try:
                toc = load_code(f, pycHeader2Magic(pyzPycMagic))
            except:
                Write.Print(f"[!] Deserialização FALHOU. Não é possível extrair {name}. Extraindo arquivos restantes.\n", Colors.red_to_yellow, interval=0.0001)

                return

            Write.Print(f"[+] Encontrados {len(toc)} arquivos no arquivo PYZ\n", Colors.green_to_cyan, interval=0.0001)


            if type(toc) == list:
                toc = dict(toc)

            for key in toc.keys():
                (ispkg, pos, length) = toc[key]
                f.seek(pos, os.SEEK_SET)
                fileName = key

                try:
                    fileName = fileName.decode("utf-8")
                except:
                    pass

                fileName = fileName.replace("..", "__").replace(".", os.path.sep)

                if ispkg == 1:
                    filePath = os.path.join(dirName, fileName, "__init__.pyc")

                else:
                    filePath = os.path.join(dirName, fileName + ".pyc")

                fileDir = os.path.dirname(filePath)
                if not os.path.exists(fileDir):
                    os.makedirs(fileDir)

                try:
                    data = f.read(length)
                    data = zlib.decompress(data)
                except:
                    try:
                        data_copy = data

                        data = self._tryDecrypt(data, "ctr")
                        data = zlib.decompress(data)
                    except:
                        try:
                            data = data_copy
                            data = self._tryDecrypt(data, "cfb")
                            data = zlib.decompress(data)
                        except:
                            print(
                                "[!] Error: Failed to decrypt & decompress {0}. Extracting as is.".format(
                                    filePath
                                )
                            )
                            open(filePath + ".encrypted", "wb").write(data_copy)
                            continue
                
                self._writePyc(filePath, data)