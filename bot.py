"""Это основной модуль бота, предназначен для непосредственного запуска.
Данный бот служит для репоста контента из аккаунтов Instagram в канал или
группу Telegram.

Параметры запуска из командной строки:
--test      : тестовый запуск скрипта - происходит однократный скрейпинг по
              одной записи с каждой страницы Instagram с пересылкой в Telegram;

--setup     : осуществляет однократный скрейпинг по одной записи с каждой
              страницы Instagram, без пересылки в Telegram; используется для
              настройки пересылки только нового контента в будущем;

--singlerun : однократный запуск скрипта, без инициации бесконечного цикла.
"""
import os
import sys
import glob
import logging
import time
import json

import telebot
from telebot.types import InputMediaPhoto, InputMediaVideo

from config_loader import (BOT_TOKEN, TEMP_FOLDER, INSTAGRAM_USER_NAMES,
                           TELEGRAM_CHAT_IDS, INCLUDE_LINK, REQUEST_TIMEOUT,
                           SEND_MESSAGE_DELAY, MAX_CAPTION_LENGTH,
                           CAPTION_TAIL, SCRAPE_PERIOD)
import scraper

bot = telebot.TeleBot(BOT_TOKEN)

def get_media_link(shortcode: str):
    return f'https://www.instagram.com/p/{shortcode}/'

def get_user_dir(username: str):
    return os.path.join(TEMP_FOLDER, username)

def get_media_file_list(path: str) -> list:
    file_list = []

    if os.path.exists(path):
        for wildcard in ['*?.*.jpg', '*?.*.mp4']:
            file_list.extend(glob.glob(os.path.join(path, wildcard)))

        file_list.sort(key=os.path.getmtime, reverse=True)

    return file_list

def get_latest_media_file(path: str) -> str:
    file_list = get_media_file_list(path)

    if file_list:
        return file_list[0]
    else:
        return False

def get_media_shortcode(file_path: str) -> str:
    return os.path.basename(file_path).split('.')[0]

def cleanup(complete=False):
    try:
        for username in INSTAGRAM_USER_NAMES:
            user_dir = get_user_dir(username)
            if not os.path.exists(user_dir):
                continue

            file_list = get_media_file_list(user_dir)

            if file_list:
                file_to_skip = file_list[0]
            else:
                file_to_skip = ''

            if complete:
                file_to_skip = ''

            for filename in os.listdir(user_dir):
                file_path = os.path.join(user_dir, filename)
                if file_path != file_to_skip:
                    os.remove(file_path)
    except OSError:
        logging.warning('Ошибка при удалении временных файлов.')

def get_media_type(file_path: str) -> str:
    """Возвращемое значение: 'photo' или 'video'.
    """
    if os.path.splitext(file_path)[1] == '.jpg':
        return 'photo'
    else:
        return 'video'

def scrape_medias(test=False) -> list:
    """Структура данных для хранения медиа представляет собой список словарей:
    [
        {
            'username': str - имя пользователя-владельца медиазаписи Instagram;
            'shortcode': str - строковый идентификатор медиазаписи Instagram;
            'caption': str - текст, относящийся к медиа;
            'files': [str,...] - список путей к скачанным файлам медиа;
        }
        ... ... ...
    ]
    """
    if test:
        cleanup(complete=True)
    else:
        cleanup()

    latest_files = {}
    for username in INSTAGRAM_USER_NAMES:
        latest_files[username] = get_latest_media_file(get_user_dir(username))

    if test:
        scraper.execute(maximum=1, latest=False)
    else:
        scraper.execute()

    medias = []

    for username in INSTAGRAM_USER_NAMES:
        items = []
        file_list = get_media_file_list(get_user_dir(username))
        for file_path in file_list:
            # if file_path == latest_files[username] and not test:
            #     break
            if file_path == latest_files[username]:
                break

            shortcode = get_media_shortcode(file_path)
            found = False
            for item in items:
                if item['shortcode'] == shortcode:
                    found = True
                    item['files'].append(file_path)
                    break
            if not found:
                items.append({'username': username,
                              'shortcode': shortcode,
                              'caption': '',
                              'files': [file_path]})

        if not items:
            continue

        try:
            with open(os.path.join(get_user_dir(username), f'{username}.json'),
                      encoding='utf-8') as f:
                media_metadata = json.load(f)
        except Exception as e:
            logging.error('Не удалось загрузить файл метаданных. ' + str(e))
        else:
            for item in items:
                try:
                    for media in media_metadata['GraphImages']:
                        if media['shortcode'] == item['shortcode']:
                            edges = media['edge_media_to_caption']['edges']
                            if edges:
                                item['caption'] = edges[0]['node']['text']
                            else:
                                item['caption'] = ''
                except Exception as e:
                    logging.error('Ошибка при разборе файла метаданных. '
                                  + str(e))

        items.reverse()
        medias.extend(items)

    return medias

def send_media_group(media: list, instagram_username: str):
    for chat_id in TELEGRAM_CHAT_IDS[instagram_username]:
        try:
            # Необходимо делать сброс позиции чтения файлов на каждой итерации
            for media_item in media:
                media_item.media.seek(0)
            bot.send_media_group(chat_id, media, timeout=REQUEST_TIMEOUT)
        except Exception as e:
            logging.error('Не удалось переслать альбом в Telegram. ' + str(e))
        else:
            logging.info('Отправлено в Telegram: альбом.')
            time.sleep(SEND_MESSAGE_DELAY)

def send_photo(photo, caption: str, instagram_username: str):
    if isinstance(photo, str):
        try:
            photo = open(photo, 'rb')
        except Exception as e:
            logging.error('Не удалось открыть файл с фото. ' + str(e))
            return

    for chat_id in TELEGRAM_CHAT_IDS[instagram_username]:
        try:
            # Сброс позиции чтения файла с фото
            photo.seek(0)
            bot.send_photo(chat_id, photo, caption=caption,
                           timeout=REQUEST_TIMEOUT)
        except Exception as e:
            logging.error(
                'Не удалось переслать фото в Telegram. ' + str(e))
        else:
            logging.info('Отправлено в Telegram: фото.')
            time.sleep(SEND_MESSAGE_DELAY)

def send_video(video, caption: str, instagram_username: str):
    if isinstance(video, str):
        try:
            video = open(video, 'rb')
        except Exception as e:
            logging.error('Не удалось открыть файл с видео. ' + str(e))
            return

    for chat_id in TELEGRAM_CHAT_IDS[instagram_username]:
        try:
            # Сброс позиции чтения файла с видео
            video.seek(0)
            bot.send_video(chat_id, video, caption=caption,
                           timeout=REQUEST_TIMEOUT)
        except Exception as e:
            logging.error(
                'Не удалось переслать видео в Telegram. ' + str(e))
        else:
            logging.info('Отправлено в Telegram: видео.')
            time.sleep(SEND_MESSAGE_DELAY)

def aggregate_to_telegram():
    logging.info('Инициирован процесс скрейпинга Instagram.')

    if '--test' in sys.argv:
        test = True
    else:
        test = False

    medias = scrape_medias(test=test)
    for media in medias:
        caption = media['caption']

        if len(caption) > MAX_CAPTION_LENGTH:
            new_len = MAX_CAPTION_LENGTH - len(CAPTION_TAIL)
            caption = caption[:new_len] + CAPTION_TAIL

        if INCLUDE_LINK:
            media_link = get_media_link(media['shortcode'])
            if caption:
                media_link = '\n' + media_link
                if len(caption + media_link) > MAX_CAPTION_LENGTH:
                    new_len = (MAX_CAPTION_LENGTH - len(CAPTION_TAIL)
                               - len(media_link))
                    caption = caption[:new_len] + CAPTION_TAIL
                caption += media_link
            else:
                caption = media_link

        if len(media['files']) > 1:
            ok_files = []
            for file_path in media['files']:
                try:
                    file = open(file_path, 'rb')
                except Exception as e:
                    logging.error('Не удалось открыть медиафайл. ' + str(e))
                else:
                    ok_files.append(file)

            if len(ok_files) > 1:
                media_items = []
                for file in ok_files:
                    if media_items:
                        actual_caption = ''
                    else:
                        actual_caption = caption

                    if get_media_type(file.name) == 'photo':
                        media_item = InputMediaPhoto(file,
                                                     caption=actual_caption)
                    else:
                        media_item = InputMediaVideo(file,
                                                     caption=actual_caption)
                    media_items.append(media_item)

                send_media_group(media_items,
                                 instagram_username=media['username'])
            elif len(ok_files) == 1:
                if get_media_type(ok_files[0].name) == 'photo':
                    send_photo(ok_files[0], caption=caption,
                               instagram_username=media['username'])
                else:
                    send_video(ok_files[0], caption=caption,
                               instagram_username=media['username'])
            else:
                logging.error('Не удалось открыть ни одного медиафайла.')

        elif len(media['files']) == 1:
            if get_media_type(media['files'][0]) == 'photo':
                send_photo(media['files'][0], caption=caption,
                           instagram_username=media['username'])
            else:
                send_video(media['files'][0], caption=caption,
                           instagram_username=media['username'])

        else:
            logging.error('Нет записей о прикреплённых файлах.')

    if not medias:
        logging.info('Обновления не найдены.')

    logging.info('Завершение процесса скрейпинга Instagram.')

def run_infinite_loop():
    logging.info('Запуск бесконечного цикла работы. '
                 + f'Период {SCRAPE_PERIOD} с.')
    while True:
        logging.info('Переход в режим ожидания.')
        time.sleep(SCRAPE_PERIOD)

        try:
            aggregate_to_telegram()
        except Exception as e:
            logging.error('Ошибка в процессе скрейпинга Instagram. ' + str(e))

def main():
    if not os.path.exists(TEMP_FOLDER):
        try:
            os.mkdir(TEMP_FOLDER)
        except OSError:
            logging.error('Не удалось создать временный каталог. '
                          'Работа программы завершается.')
            return

    if '--setup' in sys.argv:
        logging.info('Инициирован процесс начального скрейпинга Instagram '
                     + 'без репоста в Telegram.')
        scraper.execute(maximum=1, latest=False)
        logging.info('Процесс начального скрейпинга Instagram завершён.')
        return

    if ('--test' in sys.argv) or ('--singlerun' in sys.argv):
        aggregate_to_telegram()
        return

    run_infinite_loop()

if __name__ == '__main__':
    main()
