import os
import sys
from pystyle import Write, Colors
from utils.telegram import Telegram
from utils.webhookspammer import Webhook

def updateDisplayDiscord(index: int, discord: Webhook):
    os.system('clear' if sys.platform == 'nt' else 'cls')
    Write.Print(f"""
  +--------------------------------------------------+
    Nome Da Webhook -> {discord.name}
  +--------------------------------------------------+
    Spammed
    +------+
     {index}
    +------+
""", Colors.red_to_yellow, interval=0.0001)



def updateDisplayTelegram(index: int, telegram: Telegram):
    os.system('clear' if sys.platform == 'nt' else 'cls')
    Write.Print(f"""
    +--------------------------------------------------+
    Nome de usuário do bot -> {telegram.username}
    Primeiro nome do bot -> {telegram.firstName}
    Pode despejar mensagens? -> {telegram.dump}
  +--------------------------------------------------+
    Spammed
    +------+
     {index}
    +------+
""", Colors.red_to_blue, interval=0.0001)

