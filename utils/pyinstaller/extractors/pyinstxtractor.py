from __future__ import print_function
import os
import struct
import marshal
import zlib
import sys
from uuid import uuid4 as uniquename
from utils.pyinstaller.pyinstallerExceptions import ExtractionError
from pystyle import Write, Colors

class CTOCEntry:
    def __init__(self, position, cmprsdDataSize, uncmprsdDataSize, cmprsFlag, typeCmprsData, name):
        self.position = position
        self.cmprsdDataSize = cmprsdDataSize
        self.uncmprsdDataSize = uncmprsdDataSize
        self.cmprsFlag = cmprsFlag
        self.typeCmprsData = typeCmprsData
        self.name = name


class PyInstArchive:
    PYINST20_COOKIE_SIZE = 24           
    PYINST21_COOKIE_SIZE = 24 + 64      
    MAGIC = b'MEI\014\013\012\013\016'  

    def __init__(self, path):
        self.filePath = path
        self.pycMagic = b'\0' * 4
        self.barePycList = [] 
        self.entrypoints = []
        self.pyinstVer = None
        self.pymaj = None
        self.pymin = None

    def open(self):
        try:
            self.fPtr = open(self.filePath, 'rb')
            self.fileSize = os.stat(self.filePath).st_size
        except:
            ExtractionError('[!] Error: Could not open {0}\n'.format(self.filePath))
        return True


    def close(self):
        try:
            self.fPtr.close()
        except:
            pass


    def checkFile(self):
        searchChunkSize = 8192
        endPos = self.fileSize
        self.cookiePos = -1

        if endPos < len(self.MAGIC):
            Write.Print('[!] Erro: O arquivo é muito curto ou está truncado\n', Colors.red_to_yellow, interval=0.0001)

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
            ExtractionError('[!] Error : Missing cookie, unsupported pyinstaller version or not a pyinstaller archive')

        self.fPtr.seek(self.cookiePos + self.PYINST20_COOKIE_SIZE, os.SEEK_SET)

        if b'python' in self.fPtr.read(64).lower():
            Write.Print('[+] Versão do Pyinstaller: 2.1+\n', Colors.green_to_yellow, interval=0.0001)

            self.pyinstVer = 21     # pyinstaller 2.1+
        else:
            self.pyinstVer = 20     # pyinstaller 2.0
            Write.Print('[+] Versão do Pyinstaller: 2.0\n', Colors.green_to_yellow, interval=0.0001)


        return True


    def getCArchiveInfo(self):
        try:
            if self.pyinstVer == 20:
                self.fPtr.seek(self.cookiePos, os.SEEK_SET)

                (magic, lengthofPackage, toc, tocLen, pyver) = \
                struct.unpack('!8siiii', self.fPtr.read(self.PYINST20_COOKIE_SIZE))

            elif self.pyinstVer == 21:
                self.fPtr.seek(self.cookiePos, os.SEEK_SET)

                (magic, lengthofPackage, toc, tocLen, pyver, pylibname) = \
                struct.unpack('!8sIIii64s', self.fPtr.read(self.PYINST21_COOKIE_SIZE))

        except:
            ExtractionError('[!] Error : The file is not a pyinstaller archive')
            return False

        self.pymaj, self.pymin = (pyver//100, pyver%100) if pyver >= 100 else (pyver//10, pyver%10)
        Write.Print('[+] Versão do Python: {0}.{1}\n'.format(self.pymaj, self.pymin), Colors.green_to_yellow)

        tailBytes = self.fileSize - self.cookiePos - (self.PYINST20_COOKIE_SIZE if self.pyinstVer == 20 else self.PYINST21_COOKIE_SIZE)

        self.overlaySize = lengthofPackage + tailBytes
        self.overlayPos = self.fileSize - self.overlaySize
        self.tableOfContentsPos = self.overlayPos + toc
        self.tableOfContentsSize = tocLen

        Write.Print('[+] Tamanho do pacote: {0} bytes\n'.format(lengthofPackage), Colors.green_to_yellow, interval=0.0001)

        return True


    def parseTOC(self):
        self.fPtr.seek(self.tableOfContentsPos, os.SEEK_SET)

        self.tocList = []
        parsedLen = 0

        while parsedLen < self.tableOfContentsSize:
            (entrySize, ) = struct.unpack('!i', self.fPtr.read(4))
            nameLen = struct.calcsize('!iIIIBc')

            (entryPos, cmprsdDataSize, uncmprsdDataSize, cmprsFlag, typeCmprsData, name) = \
            struct.unpack( \
                '!IIIBc{0}s'.format(entrySize - nameLen), \
                self.fPtr.read(entrySize - 4))

            try:
                name = name.decode("utf-8").rstrip("\0")
            except UnicodeDecodeError:
                newName = str(uniquename())
                Write.Print('[!] Aviso: O nome do arquivo {0} contém bytes inválidos. Usando o nome aleatório {1}\n'.format(name, newName), Colors.yellow_to_red, interval=0.0001)

                name = newName
            
            if name.startswith("/"):
                name = name.lstrip("/")

            if len(name) == 0:
                name = str(uniquename())
                Write.Print('[!] Aviso: Encontrado um arquivo sem nome em CArchive. Usando o nome aleatório {0}\n'.format(name), Colors.yellow_to_red, interval=0.0001)


            self.tocList.append( \
                                CTOCEntry(                      \
                                    self.overlayPos + entryPos, \
                                    cmprsdDataSize,             \
                                    uncmprsdDataSize,           \
                                    cmprsFlag,                  \
                                    typeCmprsData,              \
                                    name                        \
                                ))

            parsedLen += entrySize
        Write.Print('[+] Encontrado {0} arquivos em CArchive\n'.format(len(self.tocList)), Colors.green_to_white, interval=0.0001)



    def _writeRawData(self, filepath, data):
        nm = filepath.replace('\\', os.path.sep).replace('/', os.path.sep).replace('..', '__')
        nmDir = os.path.dirname(nm)
        if nmDir != '' and not os.path.exists(nmDir): 
            os.makedirs(nmDir)

        with open(nm, 'wb') as f:
            f.write(data)


    def extractFiles(self):
        Write.Print('[+] Iniciando a extração... por favor, aguarde\n', Colors.green_to_white, interval=0.0001)

        extractionDir = os.path.join(os.getcwd(), os.path.basename(self.filePath) + '_extracted')

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
                    Write.Print('[!] Erro: Falha ao descomprimir {0}\n'.format(entry.name), Colors.red_to_yellow, interval=0.0001)

                    continue
                assert len(data) == entry.uncmprsdDataSize # Sanity Check

            if entry.typeCmprsData == b'd' or entry.typeCmprsData == b'o':
                continue

            basePath = os.path.dirname(entry.name)
            if basePath != '':
                if not os.path.exists(basePath):
                    os.makedirs(basePath)

            if entry.typeCmprsData == b's':
                Write.Print('[+] Ponto de entrada possível: {0}.pyc\n'.format(entry.name), Colors.green_to_yellow, interval=0.0001)

                self.entrypoints.append(entry.name + ".pyc")

                if self.pycMagic == b'\0' * 4:
                    self.barePycList.append(entry.name + '.pyc')
                self._writePyc(entry.name + '.pyc', data)

            elif entry.typeCmprsData == b'M' or entry.typeCmprsData == b'm':
                if data[2:4] == b'\r\n':
                    if self.pycMagic == b'\0' * 4: 
                        self.pycMagic = data[0:4]
                    self._writeRawData(entry.name + '.pyc', data)

                else:
                    if self.pycMagic == b'\0' * 4:
                        self.barePycList.append(entry.name + '.pyc')

                    self._writePyc(entry.name + '.pyc', data)

            else:
                self._writeRawData(entry.name, data)

                if entry.typeCmprsData == b'z' or entry.typeCmprsData == b'Z':
                    self._extractPyz(entry.name)

        self._fixBarePycs()


    def _fixBarePycs(self):
        for pycFile in self.barePycList:
            with open(pycFile, 'r+b') as pycFile:
                # Overwrite the first four bytes
                pycFile.write(self.pycMagic)


    def _writePyc(self, filename, data):
        with open(filename, 'wb') as pycFile:
            pycFile.write(self.pycMagic)            

            if self.pymaj >= 3 and self.pymin >= 7:        
                pycFile.write(b'\0' * 4)       
                pycFile.write(b'\0' * 8)       

            else:
                pycFile.write(b'\0' * 4)     
                if self.pymaj >= 3 and self.pymin >= 3:
                    pycFile.write(b'\0' * 4)  

            pycFile.write(data)


    def _extractPyz(self, name):
        dirName =  name + '_extracted'
        if not os.path.exists(dirName):
            os.mkdir(dirName)

        with open(name, 'rb') as f:
            pyzMagic = f.read(4)
            assert pyzMagic == b'PYZ\0'

            pyzPycMagic = f.read(4) 

            if self.pycMagic == b'\0' * 4:
                self.pycMagic = pyzPycMagic

            elif self.pycMagic != pyzPycMagic:
                self.pycMagic = pyzPycMagic
                Write.Print('[!] Aviso: O "magic" do pyc dos arquivos dentro do arquivo PYZ é diferente dos arquivos no CArchive\n', Colors.red_to_yellow, interval=0.0001)


            if self.pymaj != sys.version_info.major or self.pymin != sys.version_info.minor:
                Write.Print('[!] Aviso: Este script está sendo executado em uma versão do Python diferente da que foi usada para construir o executável.\n', Colors.red_to_yellow, interval=0.0001)

                Write.Print('[!] Por favor, execute este script no Python {0}.{1} para evitar erros de extração durante o descompactamento\n'.format(self.pymaj, self.pymin), Colors.red_to_yellow, interval=0.0001)

                Write.Print('[!] Pulando a extração do PYZ\n', Colors.red_to_yellow, interval=0.0001)

                return

            (tocPosition, ) = struct.unpack('!i', f.read(4))
            f.seek(tocPosition, os.SEEK_SET)

            try:
                toc = marshal.load(f)
            except:
                Write.Print('[!] Falha na deserialização. Não é possível extrair {0}. Extraindo os arquivos restantes.\n'.format(name), Colors.red_to_yellow, interval=0.0001)

                return

            Write.Print('[+] Encontrado {0} arquivos no arquivo PYZ\n'.format(len(toc)), Colors.green_to_yellow, interval=0.0001)


            if type(toc) == list:
                toc = dict(toc)

            for key in toc.keys():
                (ispkg, pos, length) = toc[key]
                f.seek(pos, os.SEEK_SET)
                fileName = key

                try:
                    fileName = fileName.decode('utf-8')
                except:
                    pass

                fileName = fileName.replace('..', '__').replace('.', os.path.sep)

                if ispkg == 1:
                    filePath = os.path.join(dirName, fileName, '__init__.pyc')

                else:
                    filePath = os.path.join(dirName, fileName + '.pyc')

                fileDir = os.path.dirname(filePath)
                if not os.path.exists(fileDir):
                    os.makedirs(fileDir)

                try:
                    data = f.read(length)
                    data = zlib.decompress(data)
                except:
                    #raise ExtractionError('[!] Error: Failed to decompress, probably encrypted.')
                    open(filePath + '.encrypted', 'wb').write(data)
                else:
                    self._writePyc(filePath, data)