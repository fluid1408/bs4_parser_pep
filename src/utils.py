from bs4 import BeautifulSoup
from exceptions import ParserFindTagException
from requests import RequestException

GET_REQUEST_ERROR = ('Возникла ошибка {request_error}'
                     'при загрузке страницы {url}')
ERROR_MESSAGE = 'Не найден тег {tag} {attrs}'

def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException as request_error:
        raise ConnectionError(GET_REQUEST_ERROR.format(
            request_error=request_error, url=url)
        )


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        raise ParserFindTagException(
            ERROR_MESSAGE.format(tag=tag, attrs=attrs)
        )
    return searched_tag


def create_soup(session, url, parser='lxml'):
    return BeautifulSoup(get_response(session, url).text, parser)
