import argparse
import json
import os
import shutil
import sys
import time
from os.path import join, dirname, exists
from pystyle import Write, Colors
 
# -================================ funcs
from methods.ben import BenDeobf
from methods.blank import BlankDeobf
from methods.empyrean import VespyDeobf
from methods.luna import LunaDeobf
from methods.notobf import NotObfuscated
from methods.outro import OtherDeobf
from utils.decompile import unzipJava, checkUPX
from utils.download import TryDownload
from utils.pyinstaller.pyinstaller import ExtractPYInstaller
from utils.pyinstaller.pyinstallerExceptions import ExtractionError
from utils.webhookspammer import Webhook
from utils.telegram import Telegram
from utils.config import Config
from utils.display import updateDisplayDiscord
from banner.show_banner import banner
# -================================ funcs


argparser = argparse.ArgumentParser(
    description="Desofuscador de Grabbers\nPor favor, dê uma estrela em https://github.com/lalaio1",
    epilog="Feito por TaxMachine"
)
argparser.add_argument(
    "filename",
    help="Arquivo para desofuscar"
)
argparser.add_argument(
    "-d", "--download",
    help="Baixar o arquivo de um link",
    action="store_true"
)
argparser.add_argument(
    "-j", "--json",
    help="Saída dos detalhes em formato JSON",
    action="store_true"
)
args = argparser.parse_args()



def ifprint(message, message_type="info"):
    symbols = {
        "success": "[+]",
        "warning": "[!]",
        "error": "[-]",
        "info": "[i]"  
    }
    colors = {
        "success": Colors.green_to_yellow,
        "warning": Colors.yellow_to_red,
        "error": Colors.red,
        "info": Colors.blue_to_cyan
    }
    symbol = symbols.get(message_type, "[i]")
    color = colors.get(message_type, Colors.blue_to_cyan)
    if not args.json:
        Write.Print(f"{symbol} {message}\n", color, interval=0.0001)

# -======================== Principal  
def main():
    JSON_EXPORT = {
        "type": None,
        "webhook": None,
        "pyinstaller_version": "0",
        "python_version": "0"
    }
    if args.download:
        ifprint("Baixando o arquivo...", "info")
        filename = TryDownload(args.filename)
        ifprint("Arquivo baixado com sucesso.", "success")

    else:
        if not os.path.exists(args.filename):
            ifprint("O arquivo não existe.", "error")


            exit(1)
        filename = args.filename
    filename = os.path.abspath(filename)
    webhook = ""
    if not exists(join(dirname(__file__), "temp")):
        os.makedirs(join(dirname(__file__), "temp"))
    if ".jar" in filename:
        ifprint("Suspeita de grabber Java, analisando strings...", "info")


        javadir = unzipJava(filename)
        ben = BenDeobf(javadir)
        webhook = ben.Deobfuscate()
        JSON_EXPORT["type"] = "java grabber"
    else:
        if checkUPX(filename):
            ifprint("Arquivo empacotado com UPX", "warning")

        try:
            archive = ExtractPYInstaller(filename)
            JSON_EXPORT["pyinstaller_version"] = str(archive.pyinstVer)
            JSON_EXPORT["python_version"] = "{0}.{1}".format(archive.pymaj, archive.pymin)
        except ExtractionError as e:
            ifprint(str(e), Colors.red_to_yellow)
            exit(1)

        extractiondir = join(os.getcwd())
        obfuscators = [
            BlankDeobf,
            LunaDeobf,
            VespyDeobf,
            OtherDeobf,
            NotObfuscated
        ]
        for deobfuscator in obfuscators:
            try:
                ifprint(f"Tentando o método {deobfuscator.__name__}", "warning")

                deobf = deobfuscator(extractiondir, archive.entrypoints)
                webhook = deobf.Deobfuscate()
                if webhook:
                    JSON_EXPORT["type"] = deobfuscator.__name__
                    break
            except Exception as e:
                ifprint(f"Falha ao tentar o método {deobfuscator.__name__}: {str(e)}", "error")

                continue
    
    if webhook == "" or webhook is None:
        ifprint("Nenhum webhook encontrado.", "error")

        sys.exit(1)

    JSON_EXPORT["webhook"] = webhook
    if args.json:
        print(json.dumps(JSON_EXPORT))
        exit(0)
    
    if type(webhook) != str:
        ifprint("Vários webhooks encontrados", "success")

        for web in webhook:
            webh = Webhook(web)
            if webh.CheckValid(web):
                ifprint(f"Webhook válido: {web}", "success")

            else:
                ifprint(f"Webhook inválido: {web}", "error")

    elif type(webhook) == str and "discord" in webhook:
        web = Webhook(webhook)
        if not web.CheckValid(webhook):
            ifprint(f"Webhook inválido: {webhook}", "error")

        else:
            web.GetInformations()
            ifprint(f"Webhook válido: {webhook}", "success")

            i = 0
            while True:
                banner()
                choice = Write.Input(
                    "\n" +
                    "[1] - Deletar webhook\n" +
                    "[2] - Spam webhook\n" +
                    "quit - para sair\n-> ", Colors.red_to_yellow, interval=0.0001
                )
                if choice == 'quit':
                    sys.exit(0)
                choice = int(choice)
                match choice:
                    case 1:
                        try:
                            web.DeleteWebhook()
                            ifprint("[+] Webhook deletado")
                        except IOError as e:
                            ifprint(str(e))
                        break
                    case 2:
                        while True:
                            try:
                                web.SendWebhook()
                                i += 1
                                updateDisplayDiscord(i, web)
                                time.sleep(0.8)
                            except IOError as e:
                                ifprint(str(e))
                                break
    else:
        webhook, chat_id = webhook.split('$')
        web = Telegram(webhook)
        if not Telegram.CheckValid(webhook):
            ifprint("[-] Token de bot do Telegram inválido")
        else:
            web.GetInformations()
            ifprint("[+] Bot do Telegram válido encontrado")
            ifprint(f"Token: {web.token}")
            ifprint(f"Username: {web.username}")
            ifprint(f"Primeiro Nome: {web.firstName}")
            ifprint(f"Pode despejar mensagens?: {web.dump}")
            ifprint("[-] Spamming ainda não implementado")


def start():
    banner()
    
    cfg = Config()
    main()
    if Webhook.GetDeleteConfig():
        shutil.rmtree(join(dirname(__file__), "temp\n"))

if __name__ == '__main__':
    start()