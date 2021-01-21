"""В данном модуле происходит подгрузка настроек бота из конфигурационного
файла и выполняется инициализация подсистемы ведения журнала ошибок (logging).
"""
import os
import logging
import logging.handlers
from configparser import ConfigParser

# Папка для сохранения файлов журнала ошибок и уведомлений
LOG_FOLDER = 'logs'

# Имя файла журнала ошибок и уведомлений
LOG_NAME = 'bot.log'

# Путь к файлу журнала ошибок и уведомлений
LOG_PATH = os.path.join(LOG_FOLDER, LOG_NAME)

# Максимальный размер файла журнала ошибок и уведомлений (в байтах)
LOG_SIZE = 2 * 1024 * 1024

# Количество файлов ротации журнала ошибок и уведомлений
LOG_BACKUPS = 2

# Название папки для сохранения временных файлов (например, загрузки)
TEMP_FOLDER = 'tmp'

# Имя конфигурационного файла
CONFIG_NAME = 'config.ini'

# Имя файла для хранения HTTP Cookies
COOKIEJAR = 'cookies.dat'

# Таймаут HTTP-запроса (секунды)
REQUEST_TIMEOUT = 30

# Задержка после отправки сообщения в Telegram (секунды)
SEND_MESSAGE_DELAY = 2

# Максимальная длина текстовой подписи к медиафайлу в Telegram
MAX_CAPTION_LENGTH = 1024

# Концовка, добавляемая к обрезанной текстовой подписи
CAPTION_TAIL = '...'

"""Настройка логгирования (журнала ошибок и уведомлений).
"""
logFormatter = logging.Formatter(fmt='[%(asctime)s] %(filename)s:%(lineno)d '
                                     '%(levelname)s - %(message)s',
                                 datefmt='%d.%m.%Y %H:%M:%S')
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

if not os.path.exists(LOG_FOLDER):
    try:
        os.mkdir(LOG_FOLDER)
    except OSError:
        logging.warning('Не удалось создать папку для журнала ошибок.')

if os.path.exists(LOG_FOLDER):
    fileHandler = logging.handlers.RotatingFileHandler(
        LOG_PATH, mode='a', maxBytes=LOG_SIZE, backupCount=LOG_BACKUPS)

    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

"""Подгрузка параметров из конфигурационного файла.
"""
parser = ConfigParser()
parser.read(CONFIG_NAME, encoding='utf-8')

try:
    # API TOKEN бота (получают у @BotFather)
    BOT_TOKEN = parser.get('credentials', 'token')

    # Названия аккаунтов пользователей Instagram для мониторинга
    INSTAGRAM_USER_NAMES = parser.get('general', 'usernames').split(',')

    # Идентификатор канала Telegram для пересылки извлечённой информации
    TELEGRAM_CHAT_ID = parser.get('general', 'channel_id')
except Exception as e:
    logging.error('Не удалось загрузить базовые настройки. '
                  'Работа программы завершается.')
    sys.exit()

# Логин владельца аккаунта Instagram
LOGIN = parser.get('credentials', 'login', fallback=None)

# Пароль владельца аккаунта Instagram
PASSWORD = parser.get('credentials', 'password', fallback=None)

# Флаг режима ручной авторизации в Instagram
MANUAL_AUTH = parser.get('credentials', 'manual_auth', fallback='')
if MANUAL_AUTH.strip().lower() in ['true', '1']:
    MANUAL_AUTH = True
else:
    MANUAL_AUTH = False

# Добавлять ли ссылку на запись Instagram в конец сообщения
INCLUDE_LINK = parser.get('general', 'include_link', fallback='')
if INCLUDE_LINK.strip().lower() in ['true', '1']:
    INCLUDE_LINK = True
else:
    INCLUDE_LINK = False

# Максимальное количество единиц медиа для каждого аккаунта Instagram,
# извлекаемое за один цикл работы скрипта
MEDIA_LIMIT = parser.get('general', 'limit', fallback='')
if MEDIA_LIMIT.strip().isdigit():
    MEDIA_LIMIT = int(MEDIA_LIMIT.strip())
else:
    MEDIA_LIMIT = 5

# Периодичность запуска скрейпинга Instagram при работе в режиме бесконечного
# цикла (секунды)
SCRAPE_PERIOD = parser.get('general', 'period', fallback='')
if SCRAPE_PERIOD.strip().isdigit():
    SCRAPE_PERIOD = int(SCRAPE_PERIOD.strip())
else:
    SCRAPE_PERIOD = 60 * 60
