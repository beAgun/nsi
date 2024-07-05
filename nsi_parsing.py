import json
import os
import zipfile
from pprint import pprint
from typing import Generator, Dict, Any, List, Tuple
import requests
import chardet
import lxml.html
from colorama import Fore, Style

from config import DATABASE_CONFIG, engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nsi_validation.utils import timer


Session = sessionmaker(bind=engine)


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

    def get_last_reference_book_version(self, identifier):
        last_version = None

        response = self.request_handler.get(
            f"https://nsi.rosminzdrav.ru/api/versions"
            f"?identifier={identifier}&size=10000"
        )
        res = response.json()
        if 'list' in res:
            for rb in res.get('list'):
                if rb.get('etalon'):
                    last_version = rb.get('version')

        print(f"last version: {last_version}")
        return last_version

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

    @timer
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

    @timer
    def get_link_download_reference_book(
        self, identifier: str, version: str, format: str = "json"
    ) -> Tuple[str, str]:
        """
        Возвращает URL для скачивания определенного справочника или связанного с ним.

        :param identifier: Идентификатор справочника.
        :param version: Версия справочника.
        :param format: Формат файла.
        :return: URL для скачивания и идентификатор справочника (возможно, связанного), который удалось скачать.
        """

        def get_link_inner(identifier: str, version: str, format: str = "json") -> str:
            response = self.request_handler.get(
                f"https://nsi.rosminzdrav.ru/api/dataFiles?identifier={identifier}&version={version}&format={format.upper()}"
            )
            res = response.json()
            if res:
                return f"https://nsi.rosminzdrav.ru/api/dataFiles/{res[0]}"
            # print(f'nth found - {identifier}, {version}')
            # print(f"https://nsi.rosminzdrav.ru/api/dataFiles?identifier={identifier}&version={version}&format={format.upper()}")

        link = get_link_inner(identifier=identifier, version=version, format=format)

        if not link:

            add_oids = self.get_additional_oids(identifier=identifier)
            # print(f'additional oids for {identifier}', add_oids)

            for additional_oid in add_oids:
                link = get_link_inner(identifier=additional_oid, version=version)
                if link:
                    identifier = additional_oid
                    break
            else:
                raise Exception(f'С сайта НСИ не удаётся скачать справочник: OID - {identifier}, версия - {version}\n'
                                f"https://nsi.rosminzdrav.ru/api/dataFiles?identifier={identifier}"
                                f"&version={version}&format={format.upper()}\n"
                                f'Возможно, стоит обновить версию')

        return link, identifier

    @timer
    def extract_and_load_json(self, url: str, format: str = "json") -> Tuple[dict, str]:
        """
        Скачивает ZIP-архив по URL, извлекает из него JSON-файл и загружает данные из файла.

        :param url: URL для скачивания файла.
        :param format: Формат файла внутри архива (по умолчанию JSON).
        :return: Данные, извлеченные из файла.
        """
        # Определение имен файлов
        zip_file_name = 'ref_books_json_files/' + url.split("/")[-1]  # Имя ZIP-файла
        json_file_name = zip_file_name.replace(
            f"_{format}.zip", f".{format}"
        )  # Преобразуем имя в формат JSON
        # print(zip_file_name, json_file_name)
        # Если json файл справочника у нас не сохранён, то скачиваем его.
        if not os.path.isfile(json_file_name):
            # Скачиваем и сохраняем ZIP-архив
            response = self.request_handler.get(url)
            with open(zip_file_name, "wb") as zip_file:
                zip_file.write(response.content)

            # Извлекаем JSON-файл из архива
            with zipfile.ZipFile(zip_file_name, "r") as zip_ref:
                zip_ref.extract(json_file_name.split('/')[1], path=json_file_name.split('/')[0])

        # Определение кодировки файла для корректного чтения
        with open(json_file_name, "rb") as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)["encoding"]

        # Читаем данные из JSON-файла с учетом его кодировки
        with open(json_file_name, "r", encoding=encoding) as file:
            data = json.load(file)

        # Удаляем временные файлы
        if os.path.isfile(zip_file_name):
            os.remove(zip_file_name)

        return data

    @staticmethod
    @timer
    def add_ref_book_to_database(oid, version, additional_oid=None):

        session = Session()

        stmt = (
                (f"""
                INSERT into NSI_Mapping (OID, version, additional_oid) 
                VALUES ('{oid}', '{version}', '{additional_oid}');""") if additional_oid
                else
                (f"""
                INSERT into NSI_Mapping (OID, version) 
                VALUES ('{oid}', '{version}');""")
        )

        try:
            print(f'{Fore.LIGHTBLUE_EX}Insertion stmt execution{Style.RESET_ALL}')
            print(stmt)
            res = session.execute(stmt).rowcount
            session.commit()
            print(f'{Fore.LIGHTBLUE_EX}{res} row inserted{Style.RESET_ALL}')
        except Exception as e:
            print(f'{Fore.RED}Stmt exception')
            print(e, Style.RESET_ALL)
        finally:
            session.close()

        """
        INSERT into NSI_Mapping (OID, version, code_column_name, name_column_name, additional_oid) 
        VALUES ('{oid}', '{version}', '{code_column_name}', '{name_column_name}', '{additional_oid}');
        """

    @staticmethod
    @timer
    def add_ref_book_code_name_to_database(oid, version, code_column_name, name_column_name):

        DATABASE_URI = (f"{DATABASE_CONFIG['engine']}://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}"
                        f"@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
                        f"?charset={DATABASE_CONFIG['charset']}")

        engine = create_engine(DATABASE_URI)
        Session = sessionmaker(bind=engine)
        session = Session()

        stmt = (f"""
        UPDATE NSI_Mapping
        SET code_column_name = '{code_column_name}', name_column_name = '{name_column_name}'
        WHERE OID = '{oid}' AND version = '{version}';""")

        try:
            print(f'{Fore.LIGHTBLUE_EX}Updating stmt execution{Style.RESET_ALL}')
            print(stmt)
            res = session.execute(stmt).rowcount
            session.commit()
            print(f'{Fore.LIGHTBLUE_EX}{res} row updated{Style.RESET_ALL}')
        except Exception as e:
            print(f'{Fore.RED}Stmt exception')
            print(e, Style.RESET_ALL)
        finally:
            session.close()

    @timer
    def get_json_file_name(self, oid: str, version: str, additional_oid: str = None) -> str:
        """
        :param oid: Идентификатор справочника.
        :param version: Версия справочника.
        :param additional_oid: Идентификатор связанного справочника,
                               из которого в дествительности вытягиваются данные.
        :return: Имя JSON файла с содержимым справочника.
        """

        json_file_name = ('ref_books_json_files/' + (additional_oid if additional_oid else oid) +
                          '_' + version + '.json')
        return json_file_name

    @timer
    def load_json_file(
            self, identifier: str, version: str, additional_oid: str = None, add_to_db: bool = False, url: str = None
    ) -> str:
        """
        Скачивает ZIP-архив по URL и извлекает из него JSON-файл, если JSON-файл не существует.
        URL определяется, если не задан.

        :param url: URL для скачивания файла.
        :param identifier: Идентификатор справочника.
        :param version: Версия справочника.
        :return: Имя загруженного файла.
        """

        # Определение имен файлов
        json_file_name = self.get_json_file_name(oid=identifier, version=version, additional_oid=additional_oid)
        if os.path.isfile(json_file_name) and not add_to_db:
            return json_file_name

        link, additional_oid = self.get_link_download_reference_book(identifier=identifier, version=version)
        # print(f'Found {identifier}, {additional_oid}, {version}')
        if add_to_db:
            if identifier != additional_oid:
                self.add_ref_book_to_database(oid=identifier, version=version, additional_oid=additional_oid)
                self.add_ref_book_to_database(oid=additional_oid, version=version, additional_oid=None)
            else:
                self.add_ref_book_to_database(oid=identifier, version=version, additional_oid=None)

        json_file_name = self.get_json_file_name(oid=identifier, version=version, additional_oid=additional_oid)
        zip_file_name = json_file_name.replace(".json", ".zip")

        # Скачиваем и сохраняем ZIP-архив
        response = self.request_handler.get(link)
        with open(os.path.join(zip_file_name), "wb") as zip_file:
            zip_file.write(response.content)

        # Извлекаем JSON-файл из архива
        with zipfile.ZipFile(zip_file_name, "r") as zip_ref:
            zip_ref.extract(json_file_name.split('/')[1], path=json_file_name.split('/')[0])

        # Удаляем временные файлы
        if os.path.isfile(zip_file_name):
            os.remove(zip_file_name)

        return json_file_name

    @timer
    def extract_json_file(self, json_file_name) -> dict:
        """
        Загружает данные из JSON файла.

        :param json_file_name: Имя JSON файла.
        :return: Данные, извлеченные из файла.
        """

        # Определение кодировки файла для корректного чтения
        # with open(json_file_name, "rb") as file:
        #     raw_data = file.read()
        #     encoding = chardet.detect(raw_data)["encoding"]
        encoding = 'utf-8'

        # Читаем данные из JSON-файла с учетом его кодировки
        with open(json_file_name, "r", encoding=encoding) as file:
            data = json.load(file)

        return data

    @timer
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

    @timer
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

    @timer
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

    def get_refbook_name(self, identifier: str):
        response = self.request_handler.get(
            f"https://nsi.rosminzdrav.ru/_next/data/f4ce7817d5ce49e22e26023344f1d282f212104a/dictionaries.json?page=1&size=20&query={identifier}"
        )
        res = response.json()
        if 'pageProps' in res:
            res = res.get('pageProps').get('list')
            if res:
                res = res[0]
                return res.get('fullName')


if __name__ == "__main__":
    request_handler = RequestHandler(verify_ssl=False)
    nsi_client = NSIClient(request_handler)
    # g = nsi_client.get_reference_books_with_rows(size=2)
    # res = next(g)
    # print(res)

    # res = nsi_client.get_additional_oids(identifier='1.2.643.5.1.13.2.1.1.156')
    # print(res)

    # g, oid = nsi_client.get_link_download_reference_book(identifier='1.2.643.5.1.13.13.11.1069', version='4.5')
    # res = nsi_client.extract_and_load_json(g)
    res = nsi_client.f()
    print(res)
    # for el in res.get('records'):
    #     code, name = el.get('code'), el.get('name')
    #     print(code, name)
    #     if el.get('data'):
    #         id, name2 = el.get('data').get('ID'), el.get('data').get('NAME')
    #         if str(id) != code:
    #             print(id)
    #         if name2 != name:
    #             print(name2)

    # d = {key: value for key, value in CDA.__dict__.items() if not key.startswith("_")}

    # for code, val in d.items():
    #     cda = nsi_client.get_cda(code)
    #     print(f'{code} = {val}')
    #     if code and cda and str(val[1]) != str(cda):
    #         print(f'---------------------------------------------------------------------------------NOT EQUAL {cda}')



    # DATABASE_URI = f"{DATABASE_CONFIG['engine']}://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}?charset={DATABASE_CONFIG['charset']}"
    #
    # engine = create_engine(DATABASE_URI)
    # Session = sessionmaker(bind=engine)
    # session = Session()
    # stmt = """
    # SELECT OID
    # FROM NSIRefBooks
    # """
    # records = session.connection().execute(stmt).fetchall()
    # # print(records)
    # oids = set(record.OID for record in records)
    # # print(*oids)
    # all_oids = set()
    # for oid in oids:
    #     add_oids = nsi_client.get_additional_oids(identifier=oid)
    #     for oid2 in add_oids:
    #         all_oids |= {oid2}
    #
    # with open('nsi_51.txt', 'w') as ouf:
    #     for oid in all_oids:
    #         name = nsi_client.get_refbook_name(identifier=oid)
    #         ouf.write(f'{oid}, {name} \n')

