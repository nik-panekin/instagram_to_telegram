import logging

import requests
from bs4 import BeautifulSoup

FREE_PROXY_HOST = 'https://free-proxy-list.net'
HTTP_BIN_HOST = 'https://httpbin.org/ip'
TIMEOUT = 5

def parse_proxies() -> list:
    proxies = []

    try:
        res = requests.get(FREE_PROXY_HOST)
        content = BeautifulSoup(res.text, 'html.parser')
        table = content.find('table')
        rows = table.find_all('tr')
        cols = [[col.text for col in row.find_all('td')] for row in rows]

        for col in cols:
            try:
                if col[4] == 'elite proxy' and col[6] == 'yes':
                    proxies.append('https://' + col[0] + ':' + col[1])
            except Exception as e:
                logging.warning(f'Парсинг {FREE_PROXY_HOST}: не удалось '
                                'выполнить разбор строки таблицы. ' + str(e))
    except Exception as e:
        logging.error(f'Ошибка парсинга {FREE_PROXY_HOST}. ' + str(e))

    return proxies

def get_valid_proxy(proxies: list) -> str:
    for proxy in proxies:
        try:
            res = requests.get(HTTP_BIN_HOST, proxies={'https': proxy},
                               timeout=TIMEOUT)
        except Exception as e:
            logging.warning(f'Ошибка доступа к прокси {proxy}. ' + str(e))
        else:
            try:
                ip = res.json()['origin']
            except Exception as e:
                logging.warning(f'Ошибка доступа через прокси {proxy}: получен'
                                ' некорректый ответ. ' + str(e))
            else:
                logging.info(f'Получен доступ через прокси. IP-адрес: {ip}.')
                return proxy

    return False

def get_proxy() -> str:
    return get_valid_proxy(parse_proxies())