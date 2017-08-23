import os
import sys
import logging
import json
import math
import random
import ast
import aiohttp
import asyncio
import async_timeout
import ssl
import string
from aiotg import Bot, chat

greeting = """
這是 Rex 的網易雲音樂解析 bot !
是基於[網易雲音樂解析](https://cm.rext.ga)的服務。
使用方式參見 /help
"""

help = """
輸入 `音樂網址 音質` 來解析
例如 : `http://music.163.com/#/m/song?id=31587429 320`
或 `音樂ID 音質`
例如 : `31587429 320`
"""

not_found = """
找不到資料 :/
"""
bye = """
掰掰! 😢
"""

global host
global api
host = os.environ.get('HOST')
api = os.environ.get('API')
logger = logging.getLogger(os.environ.get('BOT_NAME_EN'))
logChannelID = os.environ.get('LOGCHANNELID')
bot = Bot(
    api_token=os.environ.get('TOKEN'),
    name=os.environ.get('BOT_NAME_TW'),
)

async def getAdmin(ID=logChannelID):
    raw = ast.literal_eval(str(await bot.api_call("getChatAdministrators",chat_id=ID)))
    i=0
    adminDict = []

    while i < len(raw['result']):
        if 'last_name' in raw['result'][i]['user']:
            adminDict.append({
            'id':raw['result'][i]['user']['id'],
            'username':raw['result'][i]['user']['username'],
            'first_name':raw['result'][i]['user']['first_name'],
            'last_name':raw['result'][i]['user']['last_name']})
        else:
            adminDict.append({
            'id':raw['result'][i]['user']['id'],
            'username':raw['result'][i]['user']['username'],
            'first_name':raw['result'][i]['user']['first_name'],
            'last_name':''})
        i += 1
    return adminDict

async def isAdmin(ID):
    i=0
    adminList = await getAdmin()

    while i<len(adminList):
        if adminList[i]['id'] == ID:
            return True
        i += 1
    return False

async def fetch(session, url):
    with async_timeout.timeout(10):
        async with session.get(url) as response:
            return await response.text()

def idGen(sizeSettings=random.randint(5,64), charSettings='adm'):
    chars = ''
    if 'a' in charSettings:
        chars += string.ascii_letters
    if 'l' in charSettings:
        chars += string.ascii_lowercase
    if 'L' in charSettings:
        chars += string.ascii_uppercase
    if 'd' in charSettings:
        chars += string.digits
    if 'm' in charSettings:
        chars += string.punctuation

    if sizeSettings.isnumeric:
        size = sizeSettings    
    elif ',' in sizeSettings:
        sizeRange1, sizeRange2 = sizeSettings.split(',')
        size = random.randint(sizeRange1, sizeRange2)
    
    return ''.join(random.choice(chars) for _ in range(size))

async def getJSON(URL, verify_ssl=False):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=verify_ssl)) as session:
        data = await fetch(session, URL)
        return data

async def search_tracks(ID, bitrate):
    global host
    global api
    bitrate = str(int(bitrate)*1000)

    musicJson = json.loads(await getJSON(host + api +'/'+ ID +'/'+ bitrate))
    musicJson.setdefault('URL', host +'/'+ ID +'/'+ bitrate +'/'+ musicJson['sign'])
    return musicJson

def getArtist(musicJson):
    musicArtistMD = ''
    musicArtistText = ''

    for i in range(0,len(musicJson['song']['artist'])):
        musicArtistMD += ('[' + musicJson['song']['artist'][i]['name']+ ']' + '(http://music.163.com/#/artist?id=' + str(musicJson['song']['artist'][i]['id']) + ') / ')
        musicArtistText += musicJson['song']['artist'][i]['name'] + ' / '
    return {'markdown' : musicArtistMD[:-3], 'text' : musicArtistText[:-3]}

def inlineRes(music, caption=''):
    results = {
        'type': 'audio',
        'id': idGen(),
        'title' : music['song']['name'],
        'audio_url': music['URL'],
        'performer': getArtist(music)['text'],
        'caption': caption
    }

    return results
#http://music.163.com/song/33861246/?userid=18972123 320
def getMusicId(musicInfo):
    if musicInfo.isnumeric():
        return musicInfo
    elif "//music.163.com/song/" in musicInfo:
        return musicInfo.split('//music.163.com/song/')[1].split('/')[0]
    elif "song?id=" in musicInfo:
        return ''.join(i for i in musicInfo.split('id=')[1] if i.isdigit())
    else:
        return 'ERROR'

@bot.command(r'/admin')
async def admin(chat, match):
    if not await isAdmin(chat.sender['id']):
        logger.info("%s 查詢了管理員名單，遭到拒絕。", str(chat.sender))
        await bot.send_message(logChannelID, str(chat.sender) + ' 查詢了管理員名單，遭到拒絕。')
        await chat.send_text("存取遭拒。")
        return
    else:
        logger.info("%s 查詢了管理員名單", str(chat.sender))
        await bot.send_message(logChannelID, str(chat.sender) + ' 查詢了管理員名單')
        raw = await getAdmin()

        adminStr = ''
        i = 0
        while i < len(raw):
            adminStr += raw[i]['first_name']+' '+raw[i]['last_name']+'\n'
            i += 1
        await chat.send_text(adminStr)
        return

@bot.default
async def default(chat, message):
    info = message['text'].split(' ')
    musicId = ''
    if len(info) != 2:
        chat.send_text('未輸入音樂網址/ID 或音質!')
        logger.info("%s 未輸入正確的查詢參數。", str(chat.sender))
        await bot.send_message(logChannelID, str(chat.sender) + ' 未輸入正確的查詢參數。')
        return

    musicInfo, bitrate = info

    if bitrate not in ['128', '192', '320']:
        chat.send_text('音質錯誤!')
        logger.info("%s 輸入了錯誤的音質。", str(chat.sender))
        await bot.send_message(logChannelID, str(chat.sender) + ' 輸入了錯誤的音質。')
        return

    musicId = getMusicId(musicInfo)
    if not musicId.isnumeric():
        chat.send_text('輸入錯誤，無法解析!')
        logger.info("%s 的查詢發生了未知的錯誤。", str(chat.sender))
        await bot.send_message(logChannelID, str(chat.sender) + ' 的查詢發生了未知的錯誤。')
        return

    musicJson = await search_tracks(musicId, bitrate)
    musicArtist = getArtist(musicJson)
    musicInfoMD = "曲名:" + musicJson['song']['name'] + "\n歌手:" + musicArtist['markdown'] + "\n\n[解析網址](" + musicJson['URL'] +")"

    logger.info("%s 查詢了 %skbps 的 %s - %s", str(chat.sender), str(bitrate), musicArtist['text'], musicJson['song']['name'])
    await bot.send_message(logChannelID, str(chat.sender) + ' 查詢了 ' + bitrate + 'kbps 的 '+ musicArtist['text'] +' - '+ musicJson['song']['name'])

    await chat.reply(musicInfoMD, parse_mode='Markdown')
    await chat.send_audio(audio=musicJson['URL'])
    return

@bot.command(r'/start')
async def start(chat, match):
    await chat.send_text(greeting, parse_mode='Markdown')


@bot.command(r'/stop')
async def stop(chat, match):
    tuid = chat.sender["id"]
    await db.users.remove({ "id": tuid })

    logger.info("%s 退出了", chat.sender)
    await bot.send_message(logChannelID, str(chat.sender) + " 退出了")
    await chat.send_text(bye, parse_mode='Markdown')


@bot.command(r'/help')
async def usage(chat, match):
    return await chat.send_text(help, parse_mode='Markdown')

@bot.inline
async def inline(iq):
    if not iq.query:
        return await iq.answer([])

    info = iq.query.split(' ')

    if len(info) != 2:
        logger.info("[inline] %s 未輸入正確的查詢參數。", str(iq.sender))
        await iq.answer([])
        await bot.send_message(logChannelID, '[inline] ' + str(iq.sender) + ' 未輸入正確的查詢參數。')
        return

    musicInfo, bitrate = info

    if bitrate not in ['128', '192', '320']:
        logger.info("[inline] %s 輸入了錯誤的音質。", str(iq.sender))
        await iq.answer([])
        await bot.send_message(logChannelID, '[inline] ' + str(iq.sender) + ' 輸入了錯誤的音質。')
        return

    musicId = getMusicId(musicInfo)
    if not musicId.isnumeric:
        logger.info("[inline] %s 的查詢發生了未知的錯誤。", str(iq.sender))
        await iq.answer([])
        await bot.send_message(logChannelID, '[inline] ' + str(iq.sender) + ' 的查詢發生了未知的錯誤。')
        return

    musicJson = await search_tracks(musicId, bitrate)
    musicArtist = getArtist(musicJson)

    await iq.answer([inlineRes(musicJson)])
    logger.info("[inline] %s 查詢了 %skbps 的 %s - %s", str(iq.sender), str(bitrate), musicArtist['text'], musicJson['song']['name'])
    await bot.send_message(logChannelID, '[inline] ' + str(iq.sender) + ' 查詢了 ' + bitrate + 'kbps 的 '+ musicArtist['text'] +' - '+ musicJson['song']['name'])