import json
import os
import zipfile
from pprint import pprint
from typing import Generator, Dict, Any, List
import requests
import chardet
import lxml.html
import re

from utils import CDA


class RequestHandler:
    """
    Класс для отправки HTTP-запросов. Поддерживает выборочное игнорирование SSL-сертификатов.
    """

    def __init__(self, verify_ssl: bool = False):
        """
        Инициализация RequestHandler.

        :param verify_ssl: Проверять ли SSL-сертификаты.
        """
        self.verify_ssl = verify_ssl
        if not verify_ssl:
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning
            )

    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Выполняет GET-запрос.

        :param url: URL для GET-запроса.
        :return: Объект ответа requests.
        """
        return requests.get(url, verify=self.verify_ssl, **kwargs)


class NSIClient:
    """
    Клиент для работы с API NSI.
    """

    def __init__(self, request_handler: RequestHandler):
        """
        Инициализация NSIClient.

        :param request_handler: Экземпляр RequestHandler для отправки HTTP-запросов.
        """
        self.request_handler = request_handler

    def get_count_reference_books(self) -> int:
        """
        Возвращает количество доступных справочников в NSI.

        :return: Количество справочников.
        """
        response = self.request_handler.get(
            "https://nsi.rosminzdrav.ru/dictionaries?query="
        )
        tree = lxml.html.document_fromstring(response.text)
        return int(
            tree.xpath("//div[@class='list-toolbar-title']")[0]
            .text_content()
            .split()[2]
        )

    def get_reference_books(
        self, size: int = -1
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Генератор справочников из NSI.

        :param size: Количество записей на странице. По умолчанию возвращает все записи.
        :yields: Список с данными о справочниках.
        """
        size = self.get_count_reference_books() if size == -1 else size
        page = 1

        while True:
            response = self.request_handler.get(
                f"https://nsi.rosminzdrav.ru/dictionaries?page={page}&size={size}"
            )
            tree = lxml.html.document_fromstring(response.text)
            reference_books = tree.xpath("//h4[@class='ant-list-item-meta-title']/a")
            if not reference_books:
                break

            result = [
                {
                    "identifier": reference_book.get("href").split("/")[2],
                    "meta-title": reference_book.text_content(),
                    "version": reference_book.get("href").split("/")[4],
                }
                for reference_book in reference_books
            ]

            yield result
            page += 1

    def get_link_download_reference_book(
        self, identifier: str, version: str, format: str = "json"
    ) -> str:
        """
        Возвращает URL для скачивания определенного справочника.

        :param identifier: Идентификатор справочника.
        :param version: Версия справочника.
        :param format: Формат файла.
        :return: URL для скачивания.
        """
        response = self.request_handler.get(
            f"https://nsi.rosminzdrav.ru/api/dataFiles?identifier={identifier}&version={version}&format={format.upper()}"
        )
        res = response.json()
        if res:
            return f"https://nsi.rosminzdrav.ru/api/dataFiles/{res[0]}"
        else:
            print(f'nth found - {identifier}, {version}')
            print(f"https://nsi.rosminzdrav.ru/api/dataFiles?identifier={identifier}&version={version}&format={format.upper()}")

    def extract_and_load_json(self, url: str, format: str = "json") -> dict:
        """
        Скачивает ZIP-архив по URL, извлекает из него JSON-файл и загружает данные из файла.

        :param url: URL для скачивания файла.
        :param format: Формат файла внутри архива (по умолчанию JSON).
        :return: Данные, извлеченные из файла.
        """
        # Определение имен файлов
        zip_file_name = url.split("/")[-1]  # Имя ZIP-файла
        json_file_name = zip_file_name.replace(
            f"_{format}.zip", f".{format}"
        )  # Преобразуем имя в формат JSON

        # Скачиваем и сохраняем ZIP-архив
        response = self.request_handler.get(url)
        with open(zip_file_name, "wb") as zip_file:
            zip_file.write(response.content)

        # Извлекаем JSON-файл из архива
        with zipfile.ZipFile(zip_file_name, "r") as zip_ref:
            zip_ref.extract(json_file_name)

        # Определение кодировки файла для корректного чтения
        with open(json_file_name, "rb") as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)["encoding"]

        # Читаем данные из JSON-файла с учетом его кодировки
        with open(json_file_name, "r", encoding=encoding) as file:
            data = json.load(file)

        # Удаляем временные файлы
        os.remove(zip_file_name)
        os.remove(json_file_name)

        return data

    def get_reference_books_with_rows(
        self, size: int = -1
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Генератор справочников с данными о строках для каждого из них.

        :param size: Количество записей на странице.
        :yields: Справочник с данными о строках.
        """
        for reference_books in self.get_reference_books(size):
            for reference_book in reference_books:
                url = self.get_link_download_reference_book(
                    reference_book["identifier"], reference_book["version"]
                )
                reference_book["rows"] = self.extract_and_load_json(url)["records"]
            yield reference_books

    def get_additional_oids(self, identifier: str) -> list[str]:
        response = self.request_handler.get(
            f"https://nsi.rosminzdrav.ru/_next/data/f4ce7817d5ce49e22e26023344f1d282f212104a/dictionaries.json?page=1&size=20&query={identifier}"
        )
        res = response.json()
        add_oids = [identifier]
        if 'pageProps' in res:
            for rb in res.get('pageProps').get('list'):
                if 'additionalOids' in rb:
                    add_oids += rb.get('additionalOids').split(', ')
                if 'oid' in rb:
                    add_oids += rb.get('oid').split(', ')
        return set(add_oids)

    def get_cda(self, code: str) -> list[str]:
        response = self.request_handler.get(
            f"https://nsi.rosminzdrav.ru/api/data?identifier=1.2.643.5.1.13.13.99.2.197&version=4.35&query={code}&page=1&size=50&queryCount=true"
        )
        res = response.json()
        if not res:
            return 'not found'
        if not res.get('list'):
            return f"{res.get('list')}"
        return res.get('list')[0].get('NAME')



if __name__ == "__main__":
    request_handler = RequestHandler(verify_ssl=False)
    nsi_client = NSIClient(request_handler)
    # g = nsi_client.get_reference_books_with_rows(size=2)
    # res = next(g)
    # print(res)

    # res = nsi_client.get_additional_oids(identifier='1.2.643.5.1.13.2.1.1.156')
    # print(res)


    g = nsi_client.get_link_download_reference_book(identifier='1.2.643.5.1.13.13.11.1069', version='4.5')
    res = nsi_client.extract_and_load_json(g)
    for el in res.get('records'):
        code, name = el.get('code'), el.get('name')
        print(code, name)
        if el.get('data'):
            id, name2 = el.get('data').get('ID'), el.get('data').get('NAME')
            if str(id) != code:
                print(id)
            if name2 != name:
                print(name2)

    # d = {key: value for key, value in CDA.__dict__.items() if not key.startswith("_")}

    # for code, val in d.items():
    #     cda = nsi_client.get_cda(code)
    #     print(f'{code} = {val}')
    #     if code and cda and str(val[1]) != str(cda):
    #         print(f'---------------------------------------------------------------------------------NOT EQUAL {cda}')

