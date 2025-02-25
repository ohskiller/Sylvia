# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module for kanging stickers or making new ones. Thanks @rupansh"""
import os
import io
import math
import random
import urllib.request
from os import remove
import asyncio
import shlex
from typing import Tuple
import requests
from bs4 import BeautifulSoup as bs
from PIL import Image
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import (
    DocumentAttributeFilename,
    DocumentAttributeSticker,
    InputStickerSetID,
    MessageMediaPhoto,
)

from userbot import CMD_HELP, NAMEPACK, TEMP_DOWNLOAD_DIRECTORY, bot
from userbot.events import register


async def animator(media, mainevent, textevent):
    h = media.file.height
    w = media.file.width
    w, h = (-1, 512) if h > w else (512, -1)
    if not os.path.isdir(TEMP_DOWNLOAD_DIRECTORY):
        os.makedirs(TEMP_DOWNLOAD_DIRECTORY)
    temp = await mainevent.client.download_media(media, TEMP_DOWNLOAD_DIRECTORY)
    await textevent.edit("🎞 Converting into Animated sticker..")
    await runcmd(
        f"noc -ss 00:00:00 -to 00:00:02.900 -i {temp} -vf scale={w}:{h} -c:v libvpx-vp9 -crf 30 -b:v 560k -maxrate 560k -bufsize 256k -an Video.webm"
    )
    os.remove(temp)
    vid = "Video.webm"
    return vid


async def runcmd(cmd: str) -> Tuple[str, str, int, int]:
    args = shlex.split(cmd)
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return (
        stdout.decode("utf-8", "replace").strip(),
        stderr.decode("utf-8", "replace").strip(),
        process.returncode,
        process.pid,
    )

KANGING_STR = [
    "Using Witchery to kang this sticker...",
    "Plagiarising hehe...",
    "Inviting this sticker over to my pack...",
    "Kanging this sticker...",
    "Hey that's a nice sticker!\nMind if I kang?!..",
    "hehe me stel ur stikér\nhehe.",
    "Ay look over there (☉｡☉)!→\nWhile I kang this...",
    "Roses are red violets are blue, kanging this sticker so my pacc looks cool",
    "Imprisoning this sticker...",
    "Mr.Steal Your Sticker is stealing this sticker... ",
]

COMBOT = "https://combot.org/telegram/stickers?q="


@register(outgoing=True, pattern=r"^\.kang")
async def kang(args):
    """ For .kang command, kangs stickers or creates new ones. """
    user = await bot.get_me()
    if not user.username:
        user.username = user.first_name
    message = await args.get_reply_message()
    photo = None
    emojibypass = False
    is_anim = False
    is_video = False
    emoji = None

    if message and message.media:
        if isinstance(message.media, MessageMediaPhoto):
            await args.edit(f"`{random.choice(KANGING_STR)}`")
            photo = io.BytesIO()
            photo = await bot.download_media(message.photo, photo)
        elif "image" in message.media.document.mime_type.split("/"):
            await args.edit(f"`{random.choice(KANGING_STR)}`")
            photo = io.BytesIO()
            await bot.download_file(message.media.document, photo)
            if (
                DocumentAttributeFilename(file_name="sticker.webp")
                in message.media.document.attributes
            ):
                emoji = message.media.document.attributes[1].alt
                if emoji != "":
                    emojibypass = True
        elif "tgsticker" in message.media.document.mime_type:
            await args.edit(f"`{random.choice(KANGING_STR)}`")
            await bot.download_file(message.media.document, "AnimatedSticker.tgs")

            attributes = message.media.document.attributes
            for attribute in attributes:
                if isinstance(attribute, DocumentAttributeSticker):
                    emoji = attribute.alt

            emojibypass = True
            is_anim = True
            photo = 1
        elif message.media.document.mime_type in ["video/mp4", "video/webm"]:
            if message.media.document.mime_type == "video/webm":
                event = await args.edit(f"`{random.choice(KANGING_STR)}`")
                vid = await bot.download_media(
                    message.media.document, "Video.webm"
                )
            else:
                event = await args.edit("⌛ Downloading..")
                await animator(message, args, event)
                await event.edit(f"`{random.choice(KANGING_STR)}`")
            is_video = True
            emoji = "🤔"
            emojibypass = True
            photo = 1
        else:
            return await args.edit("`Unsupported File!`")
    else:
        return await args.edit("`I can't kang that...`")

    if photo:
        splat = args.text.split()
        if not emojibypass:
            emoji = "🤔"
        pack = 1
        if len(splat) == 3:
            pack = splat[2]  # User sent both
            emoji = splat[1]
        elif len(splat) == 2:
            if splat[1].isnumeric():
                # User wants to push into different pack, but is okay with
                # thonk as emote.
                pack = int(splat[1])
            else:
                # User sent just custom emote, wants to push to default
                # pack
                emoji = splat[1]
        if NAMEPACK is not None:
            packname = f"a{user.id}_by_{NAMEPACK}_{pack}"
            packnick = f"{NAMEPACK}'s kang pack Vol.{pack}"
        else:
            packname = f"a{user.id}_by_{user.username}_{pack}"
            packnick = f"@{user.username}'s kang pack Vol.{pack}"

        cmd = "/newpack"
        file = io.BytesIO()

        if is_video:
            packname += "_vid"
            packnick += " (Video)"
            cmd = "/newvideo"
        elif is_anim:
            packname += "_anim"
            packnick += " (Animated)"
            cmd = "/newanimated"
        else:
            image = await resize_photo(photo)
            file.name = "sticker.png"
            image.save(file, "PNG")

        response = urllib.request.urlopen(
            urllib.request.Request(f"http://t.me/addstickers/{packname}")
        )
        htmlstr = response.read().decode("utf8").split("\n")

        if (
            "  A <strong>Telegram</strong> user has created the <strong>Sticker&nbsp;Set</strong>."
            not in htmlstr
        ):
            async with bot.conversation("Stickers") as conv:
                await conv.send_message("/addsticker")
                await conv.get_response()
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.send_message(packname)
                x = await conv.get_response()
                limit = "50" if (is_anim or is_video) else "120"
                while limit in x.text:
                    pack += 1
                    if NAMEPACK is not None:
                        packname = f"a{user.id}_by_{NAMEPACK}_{pack}"
                        packnick = f"{NAMEPACK}'s kang pack Vol.{pack}"
                    else:
                        packname = f"a{user.id}_by_{user.username}_{pack}"
                        packnick = f"@{user.username}'s kang pack Vol.{pack}"
                    await args.edit(
                        "`Switching to Pack "
                        + str(pack)
                        + " due to insufficient space`"
                    )
                    await conv.send_message(packname)
                    x = await conv.get_response()
                    if x.text == "Invalid pack selected.":
                        await conv.send_message(cmd)
                        await conv.get_response()
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        await conv.send_message(packnick)
                        await conv.get_response()
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        if is_anim:
                            await conv.send_file("AnimatedSticker.tgs")
                            remove("AnimatedSticker.tgs")
                        elif is_video:
                            await conv.send_file("Video.webm")
                            remove("Video.webm")
                        else:
                            file.seek(0)
                            await conv.send_file(file, force_document=True)
                        await conv.get_response()
                        await conv.send_message(emoji)
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        await conv.get_response()
                        await conv.send_message("/publish")
                        if is_anim:
                            await conv.get_response()
                            await conv.send_message(f"<{packnick}>")
                        # Ensure user doesn't get spamming notifications
                        await conv.get_response()
                        await bot.send_read_acknowledge(conv.chat_id)
                        await conv.send_message("/skip")
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        await conv.get_response()
                        await conv.send_message(packname)
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        await conv.get_response()
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        return await args.edit(
                            "`Sticker added in a Different Pack !"
                            "\nThis Pack is Newly created!"
                            f"\nYour pack can be found [here](t.me/addstickers/{packname})",
                            parse_mode="md",
                        )
                if is_anim:
                    await conv.send_file("AnimatedSticker.tgs")
                    remove("AnimatedSticker.tgs")
                elif is_video:
                    await conv.send_file("Video.webm")
                    remove("Video.webm")
                else:
                    file.seek(0)
                    await conv.send_file(file, force_document=True)
                rsp = await conv.get_response()
                if "Sorry, the file type is invalid." in rsp.text:
                    return await args.edit(
                        "`Failed to add sticker, use` @Stickers `bot to add the sticker manually.`"
                    )
                await conv.send_message(emoji)
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.get_response()
                await conv.send_message("/done")
                await conv.get_response()
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
        else:
            await args.edit("`Brewing a new Pack...`")
            async with bot.conversation("Stickers") as conv:
                await conv.send_message(cmd)
                await conv.get_response()
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.send_message(packnick)
                await conv.get_response()
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                if is_anim:
                    await conv.send_file("AnimatedSticker.tgs")
                    remove("AnimatedSticker.tgs")
                elif is_video:
                    await conv.send_file("Video.webm")
                    remove("Video.webm")
                else:
                    file.seek(0)
                    await conv.send_file(file, force_document=True)
                rsp = await conv.get_response()
                if "Sorry, the file type is invalid." in rsp.text:
                    return await args.edit(
                        "`Failed to add sticker, use` @Stickers `bot to add the sticker manually.`"
                    )
                await conv.send_message(emoji)
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.get_response()
                await conv.send_message("/publish")
                if is_anim:
                    await conv.get_response()
                    await conv.send_message(f"<{packnick}>")
                # Ensure user doesn't get spamming notifications
                await conv.get_response()
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.send_message("/skip")
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.get_response()
                await conv.send_message(packname)
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.get_response()
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)

        await args.edit(
            "`Sticker kanged successfully!`"
            f"\nPack can be found [here](t.me/addstickers/{packname})",
            parse_mode="md",
        )


async def resize_photo(photo):
    """ Resize the given photo to 512x512 """
    image = Image.open(photo)
    if (image.width and image.height) < 512:
        size1 = image.width
        size2 = image.height
        if size1 > size2:
            scale = 512 / size1
            size1new = 512
            size2new = size2 * scale
        else:
            scale = 512 / size2
            size1new = size1 * scale
            size2new = 512
        size1new = math.floor(size1new)
        size2new = math.floor(size2new)
        sizenew = (size1new, size2new)
        image = image.resize(sizenew)
    else:
        maxsize = (512, 512)
        image.thumbnail(maxsize)

    return image


@register(outgoing=True, pattern=r"^\.stkrinfo$")
async def get_pack_info(event):
    if not event.is_reply:
        return await event.edit("`I can't fetch info from nothing, can I ?!`")

    rep_msg = await event.get_reply_message()
    if not rep_msg.document:
        return await event.edit("`Reply to a sticker to get the pack details`")

    try:
        stickerset_attr = rep_msg.document.attributes[1]
        await event.edit("`Fetching details of the sticker pack, please wait..`")
    except BaseException:
        return await event.edit("`This is not a sticker. Reply to a sticker.`")

    if not isinstance(stickerset_attr, DocumentAttributeSticker):
        return await event.edit("`This is not a sticker. Reply to a sticker.`")

    get_stickerset = await bot(
        GetStickerSetRequest(
            InputStickerSetID(
                id=stickerset_attr.stickerset.id,
                access_hash=stickerset_attr.stickerset.access_hash,
            )
        )
    )
    pack_emojis = []
    for document_sticker in get_stickerset.packs:
        if document_sticker.emoticon not in pack_emojis:
            pack_emojis.append(document_sticker.emoticon)

    OUTPUT = (
        f"**Sticker Title:** `{get_stickerset.set.title}\n`"
        f"**Sticker Short Name:** `{get_stickerset.set.short_name}`\n"
        f"**Official:** `{get_stickerset.set.official}`\n"
        f"**Archived:** `{get_stickerset.set.archived}`\n"
        f"**Stickers In Pack:** `{len(get_stickerset.packs)}`\n"
        f"**Emojis In Pack:**\n{' '.join(pack_emojis)}"
    )

    await event.edit(OUTPUT)


@register(outgoing=True, pattern=r"^\.get$")
async def sticker_to_png(sticker):
    if not sticker.is_reply:
        await sticker.edit("`NULL information to fetch...`")
        return False

    img = await sticker.get_reply_message()
    if not img.document:
        await sticker.edit("`Reply to a sticker...`")
        return False

    try:
        img.document.attributes[1]
    except Exception:
        await sticker.edit("`This is not a sticker...`")
        return

    with io.BytesIO() as image:
        await sticker.client.download_media(img, image)
        image.name = "sticker.png"
        image.seek(0)
        try:
            await img.reply(file=image, force_document=True)
        except Exception:
            await sticker.edit("`Err, can't send file...`")
        else:
            await sticker.delete()
    return


@register(outgoing=True, pattern=r"^\.cbs ?(.*)")
async def cb_sticker(event):
    split = event.pattern_match.group(1)
    if not split:
        await event.edit("`Provide some name to search for pack.`")
        return
    await event.edit("`Searching sticker packs`")
    text = requests.get(COMBOT + split).text
    soup = bs(text, "lxml")
    results = soup.find_all("div", {"class": "sticker-pack__header"})
    if not results:
        await event.edit("`No results found.`")
        return
    reply = f"**Sticker packs found for {split} are :**"
    for pack in results:
        if pack.button:
            packtitle = (pack.find("div", "sticker-pack__title")).get_text()
            packlink = (pack.a).get("href")
            packid = (pack.button).get("data-popup")
            reply += f"\n **• ID: **`{packid}`\n [{packtitle}]({packlink})"
    await event.edit(reply)


CMD_HELP.update(
    {
        "stickers": ">`.kang [emoji('s)]?`"
        "\nUsage: Reply .kang to a sticker or an image to kang it to your userbot pack "
        "\nor specify the emoji you want to."
        "\n\n>`.kang (emoji['s]]?` [number]?"
        "\nUsage: Kang's the sticker/image to the specified pack but uses 🤔 as emoji "
        "or choose the emoji you want to."
        "\n\n>`.stkrinfo`"
        "\nUsage: Gets info about the sticker pack."
        "\n\n>`.get`"
        "\nUsage: reply to a sticker to get 'PNG' file of sticker."
        "\n\n>`.cbs <query>`"
        "\nUsage: Search sticker pack with combot API."})
