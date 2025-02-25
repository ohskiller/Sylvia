# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.d (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module containing various scrapers. """
import json
import os
import re
import shutil
import time
from asyncio import get_event_loop, sleep
from glob import glob
from re import findall
from urllib.error import HTTPError
from urllib.parse import quote_plus
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
import wikipedia
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from emoji import replace_emoji
from googletrans import LANGUAGES, Translator
from gtts import gTTS
from gtts.lang import tts_langs
from search_engine_parser import YahooSearch as GoogleSearch
from search_engine_parser import BingSearch, GoogleSearch, YahooSearch
from search_engine_parser.core.exceptions import NoResultsOrTrafficError
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeVideo
from urbandict import define
from wikipedia import summary
from wikipedia.exceptions import DisambiguationError, PageError
from yt_dlp import YoutubeDL
from yt_dlp.utils import (
    ContentTooShortError,
    DownloadError,
    ExtractorError,
    GeoRestrictedError,
    MaxDownloadsReached,
    PostProcessingError,
    UnavailableVideoError,
    XAttrMetadataError,
)
from youtube_search import YoutubeSearch
from userbot.utils.FastTelethon import upload_file
from userbot import (
    BOTLOG,
    BOTLOG_CHATID,
    CMD_HELP,
    IMG_LIMIT,
    TEMP_DOWNLOAD_DIRECTORY,
    WOLFRAM_ID,
)
from userbot.events import register
from userbot.utils import chrome, googleimagesdownload, progress

CARBONLANG = "auto"
WIKI_LANG = "id"


@register(outgoing=True, pattern=r"^\.crblang (.*)")
async def setlang(prog):
    global CARBONLANG
    CARBONLANG = prog.pattern_match.group(1)
    await prog.edit(f"Language for carbon.now.sh set to {CARBONLANG}")


@register(outgoing=True, pattern=r"^\.carbon")
async def carbon_api(e):
    """ A Wrapper for carbon.now.sh """
    await e.edit("`Processing...`")
    CARBON = "https://carbon.now.sh/?l={lang}&code={code}"
    global CARBONLANG
    textx = await e.get_reply_message()
    pcode = e.text
    if pcode[8:]:
        pcode = str(pcode[8:])
    elif textx:
        pcode = str(textx.message)  # Importing message to module
    code = quote_plus(pcode)  # Converting to urlencoded
    await e.edit("`Processing...\n25%`")
    file_path = TEMP_DOWNLOAD_DIRECTORY + "carbon.png"
    if os.path.isfile(file_path):
        os.remove(file_path)
    url = CARBON.format(code=code, lang=CARBONLANG)
    driver = await chrome()
    driver.get(url)
    await e.edit("`Processing...\n50%`")
    driver.find_element("xpath", "//button[contains(text(),'Export')]").click()
    await e.edit("`Processing...\n75%`")
    # Waiting for downloading
    while not os.path.isfile(file_path):
        await sleep(0.5)
    await e.edit("`Processing...\n100%`")
    await e.edit("`Uploading...`")
    await e.client.send_file(
        e.chat_id,
        file_path,
        force_document=False,
        reply_to=e.message.reply_to_msg_id,
    )

    os.remove(file_path)
    driver.quit()
    # Removing carbon.png after uploading
    await e.delete()  # Deleting msg


@register(outgoing=True, pattern=r"^\.img (.*)")
async def img_sampler(event):
    """ For .img command, search and return images matching the query. """
    await event.edit("`Processing...`")
    query = event.pattern_match.group(1)
    lim = findall(r"lim=\d+", query)
    try:
        lim = lim[0]
        lim = lim.replace("lim=", "")
        query = query.replace("lim=" + lim[0], "")
    except IndexError:
        lim = IMG_LIMIT
    response = googleimagesdownload()

    # creating list of arguments
    arguments = {
        "keywords": query,
        "limit": lim,
        "format": "jpg",
        "no_directory": "no_directory",
    }

    # passing the arguments to the function
    await event.edit("`Sending some images...`")
    await sleep(5)
    await event.delete()
    paths = response.download(arguments)
    lst = paths[0][query]
    await event.client.send_file(
        await event.client.get_input_entity(event.chat_id), lst
    )
    shutil.rmtree(os.path.dirname(os.path.abspath(lst[0])))


@register(outgoing=True, pattern=r"^\.crc (.*)")
async def moni(event):
    input_str = event.pattern_match.group(1)
    input_sgra = input_str.split(" ")
    if len(input_sgra) == 3:
        try:
            number = float(input_sgra[0])
            currency_from = input_sgra[1].upper()
            currency_to = input_sgra[2].upper()
            request_url = "https://api.exchangeratesapi.io/latest?base={}".format(
                currency_from)
            current_response = get(request_url).json()
            if currency_to in current_response["rates"]:
                current_rate = float(current_response["rates"][currency_to])
                rebmun = round(number * current_rate, 2)
                await event.edit(
                    "{} {} = {} {}".format(
                        number, currency_from, rebmun, currency_to)
                )
            else:
                await event.edit(
                    "`This seems to be some alien currency, which I can't convert right now.`"
                )
        except Exception as e:
            await event.edit(str(e))
    else:
        return await event.edit("`Invalid syntax.`")


@register(outgoing=True, disable_errors=True, pattern=r"^\.google ([\s\S]*)")
async def gsearch(q_event):
    "Google search command."
    await q_event.edit("`Searching..`")
    match = q_event.pattern_match.group(1)
    page = re.findall(r"-p\d+", match)
    lim = re.findall(r"-l\d+", match)
    try:
        page = page[0]
        page = page.replace("-p", "")
        match = match.replace(f"-p{page}", "")
    except IndexError:
        page = 1
    try:
        lim = lim[0]
        lim = lim.replace("-l", "")
        match = match.replace(f"-l{lim}", "")
        lim = int(lim)
        if lim <= 0:
            lim = 5
    except IndexError:
        lim = 5
    smatch = match.replace(" ", "+")
    search_args = str(smatch), page
    gsearch = GoogleSearch()
    bsearch = BingSearch()
    ysearch = YahooSearch()
    try:
        gresults = await gsearch.async_search(*search_args)
    except NoResultsOrTrafficError:
        try:
            gresults = await bsearch.async_search(*search_args)
        except NoResultsOrTrafficError:
            try:
                gresults = await ysearch.async_search(*search_args)
            except Exception as e:
                return await q_event.edit(f"**Error:**\n`{e}`", time=10)
    msg = ""
    for i in range(lim):
        if i > len(gresults["links"]):
            break
        try:
            title = gresults["titles"][i]
            link = gresults["links"][i]
            desc = gresults["descriptions"][i]
            msg += f"🔎[{title}]({link})\n`{desc}`\n\n"
        except IndexError:
            break
    await q_event.edit(
        "**Search Query:**\n`" + match + "`\n\n**Results:**\n" + msg, link_preview=False
    )


@register(outgoing=True, pattern=r"^\.wklang (.*)")
async def setlang(wklang):
    global WIKI_LANG
    WIKI_LANG = wklang.pattern_match.group(1)
    wikipedia.set_lang(f"{WIKI_LANG}")
    await wklang.edit(f"Language for wikipedia set to {WIKI_LANG}")


@register(outgoing=True, pattern=r"^\.wiki (.*)")
async def wiki(wiki_q):
    """ For .wiki command, fetch content from Wikipedia. """
    match = wiki_q.pattern_match.group(1)
    try:
        summary(match)
    except DisambiguationError as error:
        return await wiki_q.edit(f"Disambiguated page found.\n\n{error}")
    except PageError as pageerror:
        return await wiki_q.edit(f"Page not found.\n\n{pageerror}")
    result = summary(match)
    if len(result) >= 4096:
        file = open("output.txt", "w+")
        file.write(result)
        file.close()
        await wiki_q.client.send_file(
            wiki_q.chat_id,
            "output.txt",
            reply_to=wiki_q.id,
            caption="`Output too large, sending as file`",
        )
        if os.path.exists("output.txt"):
            return os.remove("output.txt")
    await wiki_q.edit("**Search:**\n`" + match + "`\n\n**Result:**\n" + result)
    if BOTLOG:
        await wiki_q.client.send_message(
            BOTLOG_CHATID, f"Wiki query `{match}` was executed successfully"
        )


@register(outgoing=True, pattern=r"^\.ud (.*)")
async def urban_dict(ud_e):
    """ For .ud command, fetch content from Urban Dictionary. """
    await ud_e.edit("Processing...")
    query = ud_e.pattern_match.group(1)
    try:
        define(query)
    except HTTPError:
        return await ud_e.edit(f"Sorry, couldn't find any results for: {query}")
    mean = define(query)
    deflen = sum(len(i) for i in mean[0]["def"])
    exalen = sum(len(i) for i in mean[0]["example"])
    meanlen = deflen + exalen
    if int(meanlen) >= 0:
        if int(meanlen) >= 4096:
            await ud_e.edit("`Output too large, sending as file.`")
            file = open("output.txt", "w+")
            file.write(
                "Text: "
                + query
                + "\n\nMeaning: "
                + mean[0]["def"]
                + "\n\n"
                + "Example: \n"
                + mean[0]["example"]
            )
            file.close()
            await ud_e.client.send_file(
                ud_e.chat_id,
                "output.txt",
                caption="`Output was too large, sent it as a file.`",
            )
            if os.path.exists("output.txt"):
                os.remove("output.txt")
            return await ud_e.delete()
        await ud_e.edit(
            "Text: **"
            + query
            + "**\n\nMeaning: **"
            + mean[0]["def"]
            + "**\n\n"
            + "Example: \n__"
            + mean[0]["example"]
            + "__"
        )
    else:
        await ud_e.edit("No result found for **" + query + "**")


# kanged from Blank-x ;---;
@register(outgoing=True, pattern=r"^\.imdb (.*)")
async def imdb(e):
    try:
        movie_name = e.pattern_match.group(1)
        remove_space = movie_name.split(" ")
        final_name = "+".join(remove_space)
        page = get(
            "https://www.imdb.com/find?ref_=nv_sr_fn&q=" +
            final_name +
            "&s=all")
        soup = BeautifulSoup(page.content, "lxml")
        odds = soup.findAll("tr", "odd")
        mov_title = odds[0].findNext("td").findNext("td").text
        mov_link = ("http://www.imdb.com/" +
                    odds[0].findNext("td").findNext("td").a["href"])
        page1 = get(mov_link)
        soup = BeautifulSoup(page1.content, "lxml")
        if soup.find("div", "poster"):
            poster = soup.find("div", "poster").img["src"]
        else:
            poster = ""
        if soup.find("div", "title_wrapper"):
            pg = soup.find("div", "title_wrapper").findNext("div").text
            mov_details = re.sub(r"\s+", " ", pg)
        else:
            mov_details = ""
        credits = soup.findAll("div", "credit_summary_item")
        director = credits[0].a.text
        if len(credits) == 1:
            writer = "Not available"
            stars = "Not available"
        elif len(credits) > 2:
            writer = credits[1].a.text
            actors = []
            for x in credits[2].findAll("a"):
                actors.append(x.text)
            actors.pop()
            stars = actors[0] + "," + actors[1] + "," + actors[2]
        else:
            writer = "Not available"
            actors = []
            for x in credits[1].findAll("a"):
                actors.append(x.text)
            actors.pop()
            stars = actors[0] + "," + actors[1] + "," + actors[2]
        if soup.find("div", "inline canwrap"):
            story_line = soup.find(
                "div", "inline canwrap").findAll("p")[0].text
        else:
            story_line = "Not available"
        info = soup.findAll("div", "txt-block")
        if info:
            mov_country = []
            mov_language = []
            for node in info:
                a = node.findAll("a")
                for i in a:
                    if "country_of_origin" in i["href"]:
                        mov_country.append(i.text)
                    elif "primary_language" in i["href"]:
                        mov_language.append(i.text)
        if soup.findAll("div", "ratingValue"):
            for r in soup.findAll("div", "ratingValue"):
                mov_rating = r.strong["title"]
        else:
            mov_rating = "Not available"
        await e.edit(
            "<a href=" + poster + ">&#8203;</a>"
            "<b>Title : </b><code>"
            + mov_title
            + "</code>\n<code>"
            + mov_details
            + "</code>\n<b>Rating : </b><code>"
            + mov_rating
            + "</code>\n<b>Country : </b><code>"
            + mov_country[0]
            + "</code>\n<b>Language : </b><code>"
            + mov_language[0]
            + "</code>\n<b>Director : </b><code>"
            + director
            + "</code>\n<b>Writer : </b><code>"
            + writer
            + "</code>\n<b>Stars : </b><code>"
            + stars
            + "</code>\n<b>IMDB Url : </b>"
            + mov_link
            + "\n<b>Story Line : </b>"
            + story_line,
            link_preview=True,
            parse_mode="HTML",
        )
    except IndexError:
        await e.edit("Plox enter **Valid movie name** kthx")


@register(outgoing=True, pattern=r"^\.trt(?: |$)([\s\S]*)")
async def translateme(trans):
    """For .trt command, translate the given text using Google Translate."""

    if trans.is_reply and not trans.pattern_match.group(1):
        message = await trans.get_reply_message()
        message = str(message.message)
    else:
        message = str(trans.pattern_match.group(1))

    if not message:
        return await trans.edit(
            "**Give some text or reply to a message to translate!**"
        )

    await trans.edit("**Processing...**")
    translator = Translator()

    try:
        from userbot.modules.sql_helper.globals import gvarstatus
    except AttributeError:
        return await trans.edit("**Running on Non-SQL mode!**")

    if gvarstatus("trt_lang") is not None:
        target_lang = str(gvarstatus("trt_lang"))
    else:
        target_lang = "id"

    try:
        reply_text = translator.translate(
            replace_emoji(message), dest=target_lang)
    except ValueError:
        return await trans.edit(
            "**Invalid language selected, use **`.lang trt <language code>`**.**"
        )

    source_lang = LANGUAGES.get(reply_text.src).title()  # type: ignore
    target_lang = LANGUAGES.get(target_lang).title()

    # type: ignore
    reply_text = f"From: **{source_lang}**\nTo: **{target_lang}**\n\n{reply_text.text}"

    await trans.edit(reply_text)


@register(outgoing=True, pattern=r"^\.tts(?: |$)([\s\S]*)")
async def text_to_speech(query):
    """For .tts command, a wrapper for Google Text-to-Speech."""

    if query.is_reply and not query.pattern_match.group(1):
        message = await query.get_reply_message()
        message = str(message.message)
    else:
        message = str(query.pattern_match.group(1))

    if not message:
        return await query.edit(
            "**Give a text or reply to a message for Text-to-Speech!**"
        )

    await query.edit("**Processing...**")

    try:
        from userbot.modules.sql_helper.globals import gvarstatus
    except AttributeError:
        return await query.edit("**Running on Non-SQL mode!**")

    if gvarstatus("tts_lang") is not None:
        target_lang = str(gvarstatus("tts_lang"))
    else:
        target_lang = "id"

    try:
        gTTS(message, lang=target_lang)
    except AssertionError:
        return await query.edit(
            "**The text is empty.**\n"
            "Nothing left to speak after pre-precessing, tokenizing and cleaning."
        )
    except ValueError:
        return await query.edit("**Language is not supported.**")
    except RuntimeError:
        return await query.edit("**Error loading the languages dictionary.**")
    tts = gTTS(message, lang=target_lang)
    tts.save("k.mp3")
    with open("k.mp3", "rb") as audio:
        linelist = list(audio)
        linecount = len(linelist)
    if linecount == 1:
        tts = gTTS(message, lang=target_lang)
        tts.save("k.mp3")
    with open("k.mp3"):
        await query.client.send_file(query.chat_id, "k.mp3", voice_note=True)
        os.remove("k.mp3")
    await query.delete()


@register(pattern=r"\.lang (trt|tts) (.*)", outgoing=True)
async def lang(value):
    """For .lang command, change the default langauge of userbot scrapers."""
    util = value.pattern_match.group(1).lower()

    try:
        from userbot.modules.sql_helper.globals import addgvar, delgvar, gvarstatus
    except AttributeError:
        return await lang.edit("**Running on Non-SQL mode!**")

    if util == "trt":
        scraper = "Translator"
        arg = value.pattern_match.group(2).lower()

        if arg not in LANGUAGES:
            return await value.edit(
                f"**Invalid language code!**\nAvailable language codes:\n\n`{LANGUAGES}`"
            )

        if gvarstatus("trt_lang"):
            delgvar("trt_lang")
        addgvar("trt_lang", arg)
        LANG = LANGUAGES[arg]

    elif util == "tts":
        scraper = "Text to Speech"
        arg = value.pattern_match.group(2).lower()

        if arg not in tts_langs():
            return await value.edit(
                f"**Invalid language code!**\nAvailable language codes:\n\n`{tts_langs()}`"
            )

        if gvarstatus("tts_lang"):
            delgvar("tts_lang")
        addgvar("tts_lang", arg)
        LANG = tts_langs()[arg]

    await value.edit(f"**Language for {scraper} changed to {LANG.title()}.**")
    if BOTLOG:
        await value.client.send_message(
            BOTLOG_CHATID, f"`Language for {scraper} changed to {LANG.title()}.`"
        )


@register(outgoing=True, pattern=r"^\.yt (\d*) *(.*)")
async def yt_search(event):
    """ For .yt command, do a YouTube search from Telegram. """

    if event.pattern_match.group(1) != "":
        counter = int(event.pattern_match.group(1))
        if counter > 10:
            counter = int(10)
        if counter <= 0:
            counter = int(1)
    else:
        counter = int(3)

    query = event.pattern_match.group(2)

    if not query:
        return await event.edit("`Enter a query to search.`")
    await event.edit("`Processing...`")

    try:
        results = json.loads(
            YoutubeSearch(
                query,
                max_results=counter).to_json())
    except KeyError:
        return await event.edit(
            "`Youtube Search gone retard.\nCan't search this query!`"
        )

    output = f"**Search Query:**\n`{query}`\n\n**Results:**\n"

    for i in results["videos"]:
        try:
            title = i["title"]
            link = "https://youtube.com" + i["url_suffix"]
            channel = i["channel"]
            duration = i["duration"]
            views = i["views"]
            output += f"[{title}]({link})\nChannel: `{channel}`\nDuration: {duration} | {views}\n\n"
        except IndexError:
            break

    await event.edit(output, link_preview=False)


@register(outgoing=True, pattern=r"^\.rip(audio|video( \d{0,4})?) (.*)")
async def download_video(v_url):
    """For .rip command, download media from YouTube and many other sites."""
    dl_type = v_url.pattern_match.group(1).lower()
    reso = v_url.pattern_match.group(2)
    reso = reso.strip() if reso else None
    url = v_url.pattern_match.group(3)

    await v_url.edit("`Preparing to download...`")
    s_time = time.time()
    video = False
    audio = False

    # handle tiktok link
    if "tiktok.com" in url:
        async with ClientSession() as ses, ses.head(
            url, allow_redirects=True, timeout=5
        ) as head:
            url = str(head.url)

    if "audio" in dl_type:
        opts = {
            "format": "bestaudio",
            "addmetadata": True,
            "key": "FFmpegMetadata",
            "writethumbnail": True,
            "prefer_ffmpeg": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }
            ],
            "outtmpl": os.path.join(
                TEMP_DOWNLOAD_DIRECTORY, str(s_time), "%(title)s.%(ext)s"
            ),
            "quiet": True,
            "logtostderr": False,
            "ffmpeg_location": "/bin/noc",
        }
        audio = True
    elif "video" in dl_type:
        quality = (
            f"bestvideo[height<={reso}]+bestaudio/best[height<={reso}]"
            if reso
            else "bestvideo+bestaudio/best"
        )
        opts = {
            "format": quality,
            "addmetadata": True,
            "key": "FFmpegMetadata",
            "prefer_ffmpeg": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "outtmpl": os.path.join(
                TEMP_DOWNLOAD_DIRECTORY, str(s_time), "%(title)s.%(ext)s"
            ),
            "logtostderr": False,
            "quiet": True,
            "ffmpeg_location": "/bin/noc",
        }
        video = True

    try:
        await v_url.edit("`Fetching data, please wait..`")
        with YoutubeDL(opts) as rip:
            rip_data = rip.extract_info(url)
    except DownloadError as DE:
        return await v_url.edit(f"`{str(DE)}`")
    except ContentTooShortError:
        return await v_url.edit("`The download content was too short.`")
    except GeoRestrictedError:
        return await v_url.edit(
            "`Video is not available from your geographic location "
            "due to geographic restrictions imposed by a website.`"
        )
    except MaxDownloadsReached:
        return await v_url.edit("`Max-downloads limit has been reached.`")
    except PostProcessingError:
        return await v_url.edit("`There was an error during post processing.`")
    except UnavailableVideoError:
        return await v_url.edit("`Media is not available in the requested format.`")
    except XAttrMetadataError as XAME:
        return await v_url.edit(f"`{XAME.code}: {XAME.msg}\n{XAME.reason}`")
    except ExtractorError:
        return await v_url.edit("`There was an error during info extraction.`")
    except Exception as e:
        return await v_url.edit(f"{str(type(e))}: {str(e)}")
    c_time = time.time()
    if audio:
        await v_url.edit(
            f"`Preparing to upload song:`\n**{rip_data.get('title')}**"
            f"\nby **{rip_data.get('uploader')}**"
        )
        f_name = glob(
            os.path.join(
                TEMP_DOWNLOAD_DIRECTORY,
                str(s_time),
                "*.mp3"))[0]
        with open(f_name, "rb") as f:
            result = await upload_file(
                client=v_url.client,
                file=f,
                name=f_name,
                progress_callback=lambda d, t: get_event_loop().create_task(
                    progress(
                        d, t, v_url, c_time,
                        "Uploading..", f"{rip_data['title']}.mp3"
                    )
                ),
            )

        thumb_image = [
            x
            for x in glob(os.path.join(TEMP_DOWNLOAD_DIRECTORY, str(s_time), "*"))
            if not x.endswith(".mp3")
        ][0]
        metadata = extractMetadata(createParser(f_name))
        duration = 0
        if metadata and metadata.has("duration"):
            duration = metadata.get("duration").seconds
        await v_url.client.send_file(
            v_url.chat_id,
            result,
            supports_streaming=True,
            attributes=[
                DocumentAttributeAudio(
                    duration=duration,
                    title=rip_data.get("title"),
                    performer=rip_data.get("uploader"),
                )
            ],
            thumb=thumb_image,
        )
        await v_url.delete()
    elif video:
        await v_url.edit(
            f"`Preparing to upload video:`\n**{rip_data.get('title')}**"
            f"\nby **{rip_data.get('uploader')}**"
        )
        f_path = glob(
            os.path.join(
                TEMP_DOWNLOAD_DIRECTORY,
                str(s_time),
                "*"))[0]
        # Noob way to convert from .mkv to .mp4
        if f_path.endswith(".mkv"):
            base = os.path.splitext(f_path)[0]
            os.rename(f_path, base + ".mp4")
            f_path = glob(
                os.path.join(
                    TEMP_DOWNLOAD_DIRECTORY,
                    str(s_time),
                    "*"))[0]
        f_name = os.path.basename(f_path)
        with open(f_path, "rb") as f:
            result = await upload_file(
                client=v_url.client,
                file=f,
                name=f_name,
                progress_callback=lambda d, t: get_event_loop().create_task(
                    progress(d, t, v_url, c_time, "Uploading..", f_name)
                ),
            )
        metadata = extractMetadata(createParser(f_path))
        duration = 0
        width = 0
        height = 0
        if metadata:
            if metadata.has("duration"):
                duration = metadata.get("duration").seconds
            if metadata.has("width"):
                width = metadata.get("width")
            if metadata.has("height"):
                height = metadata.get("height")
        await v_url.client.send_file(
            v_url.chat_id,
            result,
            attributes=[
                DocumentAttributeVideo(
                    duration=duration,
                    w=width,
                    h=height,
                    supports_streaming=True,
                )
            ],
            caption=f"[{rip_data.get('title')}]({url})",
        )
        await v_url.delete()


@register(outgoing=True, pattern=r"^\.wolfram (.*)")
async def wolfram(wvent):
    if WOLFRAM_ID is None:
        await wvent.edit(
            "Please set your WOLFRAM_ID first !\n"
            "Get your API KEY from [here](https://"
            "products.wolframalpha.com/api/)",
            parse_mode="Markdown",
        )
        return
    i = wvent.pattern_match.group(1)
    appid = WOLFRAM_ID
    server = f"https://api.wolframalpha.com/v1/spoken?appid={appid}&i={i}"
    res = get(server)
    await wvent.edit(f"**{i}**\n\n" + res.text, parse_mode="Markdown")
    if BOTLOG:
        await wvent.client.send_message(
            BOTLOG_CHATID, f".wolfram {i} was executed successfully"
        )


CMD_HELP.update(
    {
        "img": ">`.img <search_query>`"
        "\nUsage: Does an image search on Google and shows **IMG_LIMIT** images.",
        "currency": ">`.crc <amount> <from> <to>`"
        "\nUsage: Converts various currencies for you.",
        "carbon": ">`.carbon <text> [or reply]`"
        "\nUsage: Beautify your code using carbon.now.sh\n"
        "Use .crblang <text> to set language for your code.",
        "google": ">`.google <query>`"
        "\nUsage: Does a search on Google.",
        "wiki": ">`.wiki <query>`"
        "\nUsage: Does a search on Wikipedia.\n"
        ">`.wklang` <language code> (Default is Indonesian)"
        "\nUsage: Set language for wikipedia.",
        "ud": ">`.ud <query>`"
        "\nUsage: Does a search on Urban Dictionary.",
        "tts": ">`.tts <text> [or reply]`"
        "\nUsage: Translates text to speech for the language which is set."
        "\nUse >`.lang tts <language code>` to set language for tts. (Default is Indonesian.)",
        "trt": ">`.trt <text> [or reply]`"
        "\nUsage: Translates text to the language which is set."
        "\nUse >`.lang trt <language code>` to set language for trt. (Default is Indonesian)",
        "yt": ">`.yt <count> <query>`"
        "\nUsage: Does a YouTube search."
        "\nCan specify the number of results needed (default is 3).",
        "imdb": ">`.imdb <movie-name>`"
        "\nUsage: Shows movie info and other stuff.",
        "rip": ">`.ripaudio <url>`"
        "\nUsage: Download videos from YouTube and convert to audio "
        "\n\n>`.ripvideo <quality> <url>` (quality is optional)"
        "\nQuality examples : `144` `240` `360` `480` `720` `1080` `2160`"
        "\nUsage: Download videos from YouTube"
        "\n\n[Other supported sites](https://ytdl-org.github.io/youtube-dl/supportedsites.html)",
        "wolfram": ">`.wolfram` <query>"
        "\nUsage: Get answers to questions using WolframAlpha Spoken Results API",
    })
