import logging
import re
from collections import defaultdict
from urllib.parse import urljoin

import requests_cache
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (BASE_DIR, DOWNLOAD_FOLDER, EXPECTED_STATUS,
                       MAIN_DOC_URL, PEP_URL)
from exceptions import ParserNotFindVersion
from outputs import control_output
from utils import create_soup, find_tag, get_response

PARSER_START = 'Парсер запущен!'
PARSER_FINISHED = 'Парсер завершил работу.'
ARGUMENT_INFO = 'Аргументы командной строки: {args}'
ARCHIVE_DOWNLOAD_FINISHED = 'Архив был загружен и сохранён: {archive_path}'
ERROR_FINDING_LIST = 'Не найден список c версиями Python'
MAIN_EXCEPTION_ERROR = 'Ошибка: {error}'
ERROR_MESSAGE = 'Возникла ошибка при загрузке страницы {link}'
UNMATCH_STATUSES_MESSAGE = ('Несовпадающие статусы:\n'
                            '{pep_link}\n'
                            'Статус в карточке: {status}\n'
                            'Ожидаемые статусы: {expected_status}')


def whats_new(session):
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    logs = []
    for a_tag in tqdm(
        create_soup(
            session, urljoin(MAIN_DOC_URL, 'whatsnew/')
        ).select(
            '#what-s-new-in-python div.toctree-wrapper li.toctree-l1 > a'
        )
    ):
        version_link = urljoin(
            urljoin(MAIN_DOC_URL, 'whatsnew/'), a_tag['href']
        )
        try:
            soup = create_soup(session, version_link)
        except ConnectionError:
            logs.append(ERROR_MESSAGE.format(link=version_link))
            continue
        results.append(
            (version_link,
             find_tag(soup, 'h1').text.replace('¶', ''),
             find_tag(soup, 'dl').text.replace('\n', ''))
        )
    list(map(logging.error, logs))
    return results


def latest_versions(session):
    results = [('Ссылка на документацию', 'Версия', 'Статус'), ]
    sidebar = find_tag(
        get_response(MAIN_DOC_URL, session),
        'div',
        {'class': 'sphinxsidebarwrapper'}
    )
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
        else:
            raise ParserNotFindVersion(ERROR_FINDING_LIST)

    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (a_tag['href'], version, status)
        )
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = create_soup(session, downloads_url)
    pdf_a4_link = soup.select_one(
        'div.body td > a[href$="pdf-a4.zip"]'
    )['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / DOWNLOAD_FOLDER
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(ARCHIVE_DOWNLOAD_FINISHED)


def pep(session):
    results = defaultdict(int)
    logs = []
    unmatch_statuses = []
    for table in create_soup(session, PEP_URL).select(
        '#pep-content #index-by-category table,'
        '#numerical-index table,'
        '#reserved-pep-numbers table'
    ):
        tbody_tag = find_tag(table, 'tbody')
        tbody_tr_tags = tbody_tag.find_all('tr')
        for tbody_tr_tag in tqdm(tbody_tr_tags):
            first_column_tag = find_tag(tbody_tr_tag, 'td')
            preview_status = first_column_tag.text[1:]
            a_tag = find_tag(
                tbody_tr_tag, 'a', attrs={'class': 'pep reference internal'}
            )
            pep_link = urljoin(PEP_URL, a_tag['href'])
            try:
                soup = create_soup(session, pep_link)
            except ConnectionError:
                logs.append(ERROR_MESSAGE.format(link=pep_link))
                continue
            for dt_tag in soup.find_all('dt'):
                status = dt_tag.find_next_sibling().string
                if dt_tag.text != 'Status:':
                    continue
                if status not in EXPECTED_STATUS[preview_status]:
                    unmatch_statuses.append(
                        UNMATCH_STATUSES_MESSAGE.format(
                            pep_link=pep_link,
                            status=status,
                            expected_status=EXPECTED_STATUS[preview_status]
                        )
                    )
                results[status] += 1

    list(map(logging.error, logs))
    list(map(logging.warning, unmatch_statuses))
    return (
        ('Статус', 'Количество'),
        *results.items(),
        ('Всего', sum(results.values())),
    )


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    logging.info(PARSER_START)
    try:
        configure_logging()
        arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
        args = arg_parser.parse_args()
        logging.info(ARGUMENT_INFO.format(args=args))
        session = requests_cache.CachedSession()
        if args.clear_cache:
            session.cache.clear()
        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)
        if results is not None:
            control_output(results, args)
        logging.info(PARSER_FINISHED)
    except Exception as error:
        logging.error(MAIN_EXCEPTION_ERROR.format(error=error))


if __name__ == '__main__':
    main()
