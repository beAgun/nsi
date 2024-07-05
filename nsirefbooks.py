import re
import time
from pprint import pprint
from lxml.etree import _Element
from lxml import etree
from nsi_parsing import NSIClient, RequestHandler
from colorama import Fore, Style
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from nsi_validation.config import USE_TIMER, SUCCESSFUL_LOG
from nsi_validation.utils import timer, get_xml_doc, get_tag, get_namespace, find_ancestors, get_parent_map
from nsi_validation.config import engine

ACC = 0


Session = sessionmaker(bind=engine)


class XMLPathDescriptor:
    def __init__(self):
        self._value = None
        self._owner = None

    def __get__(self, instance, owner):
        return self._value

    def __set__(self, instance, value):
        self._value = value
        print('setter')
        if self._owner is None:
            self._owner = type(instance)
        self._owner._xml_data = get_xml_doc(self._owner._xml_path)
        self._owner. _xml_tree = etree.fromstring(self._owner._xml_data)


class RefBook:
    """
    Класс для элементов XML документа, у которых
    есть атрибуты code (код),
                  codeSystem (OID справочника),
                  codeSystemVersion (версия справочника),
                  displayName (наименование),
    где код и наименование тянутся из справочника.
    """

    xml_path = None
    _xml_data = None
    _xml_tree = None
    _parent_map = None

    @classmethod
    def set_xml_path(cls, xml_path):
        cls.xml_path = xml_path
        cls._xml_data = get_xml_doc(cls.xml_path)
        cls._xml_tree = etree.fromstring(cls._xml_data)
        cls._parent_map = get_parent_map(cls._xml_tree)

    def __new__(cls, *args, **kwargs):
        if cls.xml_path is None:
            raise Exception("You can't create RefBook object without setting the path"
                            "with `set_xml_path` method")
        return super().__new__(cls)

    def __init__(self, element: _Element, etalon=False):
        self.tag = get_tag(element)
        self.namespace = get_namespace(element)

        kwargs = element.attrib

        self.code = kwargs.get('code')
        self.codeSystem = kwargs.get('codeSystem')
        self.codeSystemVersion = kwargs.get('codeSystemVersion')
        self.codeSystemName = kwargs.get('codeSystemName')
        self.displayName = kwargs.get('displayName')

        self.etalon = etalon
        self.path = find_ancestors(element, self._parent_map)

    def __repr__(self):
        return str(self.__dict__) + '\n'

    def print_attribs(self, other=None):
        print(self.__dict__.get('path'))
        if other is not None:
            correct_res = 'Одинаковые атрибуты: ' + '\n'
            wrong_res = 'Неодинаковые атрибуты: ' + '\n'
            for attr_name in self.__dict__:
                if attr_name not in ('etalon', 'path', 'tag', 'namespace'):
                    if self.__dict__.get(attr_name) == other.__dict__.get(attr_name):
                        correct_res += (f'{attr_name} - {"в эталоне" if self.etalon else "в формируемом"}: {self.__dict__.get(attr_name)}, '
                                f'{"в эталоне" if other.etalon else "в формируемом"}: {other.__dict__.get(attr_name)}') + '\n'
                    else:
                        wrong_res += (f'{attr_name} - {"в эталоне" if self.etalon else "в формируемом"}: {self.__dict__.get(attr_name)}, '
                                f'{"в эталоне" if other.etalon else "в формируемом"}: {other.__dict__.get(attr_name)}') + '\n'
            print(correct_res, wrong_res, sep='\n')
        else:
            res = 'Атрибуты' + (' в формируемом:' if not self.etalon else ' в эталоне') + '\n'
            for attr_name in self.__dict__:
                if attr_name not in ('etalon', 'path', 'tag', 'namespace'):
                    res += f'{attr_name} - {self.__dict__.get(attr_name)}' + '\n'
            print(res)

    def __eq__(self, other):
        if isinstance(other, RefBook):
            if (self.codeSystem == other.codeSystem and
                    self.codeSystemName == other.codeSystemName and
                    self.codeSystemVersion == other.codeSystemVersion):
                return True
            elif self.codeSystem == other.codeSystem:
                return True
        return NotImplemented


# def get_elements_by_name(
#         parent_element, elem_namespace, elem_name: str, ns: dict, elem_cls, parents, etalon=False
# ):
#
#     elems = parent_element.xpath(f'//{elem_namespace}:' + f'{elem_name}', namespaces=ns)
#     elems_attrib = []
#     for i, elem in enumerate(elems):
#         elem.attrib['path'] = find_ancestors(elem, parents)[1]
#         elems_attrib += [elem_cls(elem.attrib, etalon)]
#         if elem.attrib.get('codeSystem') is None:
#             print(f'{i} {elem_name} is None')
#             ancestors = find_ancestors(elem, parents)
#
#     return elems_attrib


def get_elements_by_attribute(xml_tree, attr_name: str):
    elements = []
    for elem in xml_tree.iter():
        if attr_name in elem.attrib:
            elements += [elem]
    return elements


@timer
def check_name_for_not_existing_ref_book(data, element):
    all_ans = []
    any_found_matching = 0

    found = 0
    found_matching = 0
    global cnt_right
    global cnt_found_matching

    key_code_name_array = []
    record_indexs = set()
    records = data.get('records')

    for record_index, record in enumerate(records):
        d = {**record, **record.get('data')} if record.get('data') else record
        for code_key, code_value in d.items():
            if element.code == str(code_value):
                found = 1
                for name_key, name_value in d.items():
                    if element.displayName.strip() == name_value:
                        cnt_right += 1
                        key_code_name_array += [(code_key, name_key)]
                        # print(f'совпадают имена: \n {el.displayName}')
                        # print(record)
                        found_matching = 1
                        any_found_matching = 1
                    else:
                        record_indexs |= {record_index}

    if not found:
        print(f'{Fore.RED}В справочнике с сайта НСИ не найдены записи с кодом {element.code},\n'
              f'OID: {element.codeSystem}, version: {element.codeSystemVersion}{Style.RESET_ALL}')
        print(f"\n{Fore.RED}В сформированном документе:{Style.RESET_ALL}")
        print()
        pprint(element.__dict__)

    elif not found_matching:
        for i in record_indexs:
            all_ans += [records[i]]

        key_code_name_array = [(key, val) for key, val in data['records'][-1].items()]
        if data['records'][-1].get('data'):
            key_code_name_array += [(key, val) for key, val in data['records'][-1].get('data').items()]
        for i, pair in enumerate(key_code_name_array):
            print(f'{i + 1}) {pair[0]}: {pair[1]}')
        code_option = int(input("Какой из вариантов занести в таблицу в качестве кода? (цифра)  "))
        name_option = int(input("Какой из вариантов занести в таблицу в качестве наименования? (цифра)  "))

        key_code, key_name = key_code_name_array[code_option - 1][0], key_code_name_array[name_option - 1][0]

        NSIClient.add_ref_book_code_name_to_database(oid=element.codeSystem, version=element.codeSystemVersion,
                                                     code_column_name=key_code, name_column_name=key_name)
    else:
        if SUCCESSFUL_LOG:
            print(Fore.GREEN, '*' * 40, 'OK', '*' * 40, Style.RESET_ALL, sep='')

        print(data['records'][-1])
        if len(key_code_name_array) > 1:
            for i, val in enumerate(key_code_name_array):
                print(f'{i + 1}) {val}')
            option = int(input("Какой из вариантов занести в таблицу? (цифра)  "))
        else:
            option = 1

        key_code, key_name = key_code_name_array[option - 1]

        NSIClient.add_ref_book_code_name_to_database(oid=element.codeSystem, version=element.codeSystemVersion,
                                                      code_column_name=key_code, name_column_name=key_name)

        cnt_found_matching += 1

    return any_found_matching, cnt_found_matching, all_ans

@timer
def check_name_for_existing_ref_book(data, element, code, name):
    all_ans = []
    any_found_matching = 0

    found = 0
    found_matching = 0
    global cnt_right
    global cnt_found_matching

    record_indexs = set()
    records = data.get('records')

    for record_index, record in enumerate(records):
        d = {**record, **record.get('data')} if record.get('data') else record
        code_value, name_value = str(d.get(code)), str(d.get(name))
        if code_value and name_value:
            if element.code == code_value:
                found = 1
                if element.displayName.strip() == name_value:
                    cnt_right += 1
                    # print(f'совпадают имена: \n {el.displayName}')
                    # print(record)
                    found_matching = 1
                    any_found_matching = 1
                else:
                    record_indexs |= {record_index}

    if not found:
        print(f'{Fore.RED}В справочнике с сайта НСИ не найдены записи с кодом {element.code},\n'
              f'OID: {element.codeSystem}, version: {element.codeSystemVersion}{Style.RESET_ALL}')
        print(f"\n{Fore.RED}В сформированном документе:{Style.RESET_ALL}")
        pprint(element.__dict__)
        print()

    elif not found_matching:
        for i in record_indexs:
            all_ans += [records[i]]

    else:
        if SUCCESSFUL_LOG:
            print(Fore.GREEN, '*' * 40, 'OK', '*' * 40, Style.RESET_ALL, sep='')

        cnt_found_matching += 1

    return any_found_matching, cnt_found_matching, all_ans


@timer
def get_records(elements):
    metadata = MetaData()
    table = Table('NSI_Mapping', metadata, autoload_with=engine)
    oids = [el.codeSystem for el in elements]
    versions = [el.codeSystemVersion for el in elements]

    session = Session()
    query = session.query(table).filter(table.c.OID.in_(oids), table.c.version.in_(versions))
    results = query.all()
    session.close()
    results_dict = {(record.OID, record.version): record for record in results}
    return results_dict


@timer
def get_record(results_dict, oid, version):
    return results_dict.get((oid, version))


@timer
def get_record_2(oid, version):
    stmt = """
                SELECT t1.*
                FROM NSI_Mapping t1
                WHERE t1.OID = '{oid}' AND t1.version = '{version}';
                """.format(oid=oid, version=version)
    session = Session()
    res = session.execute(stmt).fetchone()
    session.close()
    return res


@timer
def compare_ref_books_names(elements):
    result = ''
    global cnt_right
    cnt_right = 0
    global cnt_found_matching
    cnt_found_matching = 0
    i = 0

    request_handler = RequestHandler(verify_ssl=False)
    nsi_client = NSIClient(request_handler)

    # Вариант с одним запросом для всех справочников
    # results_dict = get_records(elements)

    for el in elements:
        i += 1
        if SUCCESSFUL_LOG or USE_TIMER:
            print('-' * 100 + str(i) + '-' * 100)

        # Вариант с одним запросом для всех справочников
        # res = get_record(results_dict, oid=el.codeSystem, version=el.codeSystemVersion)

        # Вариант с одним запросом для отдельного справочника
        res = get_record_2(oid=el.codeSystem, version=el.codeSystemVersion)

        file = nsi_client.load_json_file(identifier=el.codeSystem,
                                         version=el.codeSystemVersion,
                                         additional_oid=res.additional_oid if res else None,
                                         add_to_db=not res)

        if SUCCESSFUL_LOG:
            print(f'{Fore.GREEN}Найден файл справочника {file}{Style.RESET_ALL}')
        data = nsi_client.extract_json_file(file)

        if res and res.code_column_name and res.name_column_name:
            any_found_matching, cnt_found_matching, all_ans = check_name_for_existing_ref_book(
                data, el, res.code_column_name, res.name_column_name
            )
        else:
            any_found_matching, cnt_found_matching, all_ans = check_name_for_not_existing_ref_book(data, el)

        if not any_found_matching and all_ans:
            result += (
                f"{Fore.RED}В справочнике с сайта НСИ найдены записи с таким же кодом, но другими наименованиями\n"
                f"В НСИ:{Style.RESET_ALL}" +
                str(all_ans) +
                f"\n{Fore.RED}В сформированном документе:{Style.RESET_ALL}" +
                str(el.__dict__) + '\n'
            )
            print(f"{Fore.RED}В справочнике с сайта НСИ найдены записи с таким же кодом, но другими наименованиями\n"
                  f"В НСИ:{Style.RESET_ALL}")
            pprint(all_ans)
            print(f"\n{Fore.RED}В сформированном документе:{Style.RESET_ALL}")
            pprint(el.__dict__)

        elif all_ans:
            result += '\n'.join(str(all_ans))
            pprint(all_ans)

        if SUCCESSFUL_LOG or USE_TIMER:
            print('-' * 100 + str(i) + '-' * 100 + '\n\n\n')

    if cnt_found_matching == len(elements):
        print('Успешно!')
    print(f'\n{Fore.BLUE}Всего элементов с атрибутами (code, codeSystem, codeSystemVersion, displayName)'
          f' в xml: {len(elements)}, '
          f'всего правильно указанных атрибутов displayName: {cnt_found_matching}{Style.RESET_ALL}')

    return (
            result + ('Успешно!' if cnt_found_matching == len(elements) else '') +
            f'\n{Fore.BLUE}Всего элементов с атрибутами (code, codeSystem, codeSystemVersion, displayName)'
            f' в xml: {len(elements)}, '
            f'всего правильно указанных атрибутов displayName: {cnt_found_matching}{Style.RESET_ALL}'
    )


def get_ref_book_elements_by_attribute(xml_path, attribute):


    RefBook.set_xml_path(xml_path)
    # RefBook.xml_path = xml_path
    # RefBook._xml_data = get_xml_doc(xml_path)
    # RefBook._xml_tree = etree.fromstring(RefBook._xml_data)


    RefBook_elements = []
    OIDs = tuple()
    lxml_elements = get_elements_by_attribute(RefBook._xml_tree, attribute)

    for el in lxml_elements:
        rb_el = RefBook(el)

        if not re.match(r"(\d+\.\d+)", rb_el.codeSystem):
            continue

        if rb_el.codeSystem and rb_el.code and rb_el.codeSystemVersion and rb_el.displayName:
            # print(rb_el.codeSystem, rb_el.codeSystemVersion, rb_el.displayName)
            RefBook_elements += [rb_el]
            OIDs += (rb_el.codeSystem,)

    return RefBook_elements


if __name__ == "__main__":
    t0 = time.perf_counter()

    elements = get_ref_book_elements_by_attribute(
        xml_path='/home/vista/PycharmProjects/vista3/resp.xml',
        attribute='codeSystem'
    )
    result = compare_ref_books_names(elements=elements)
    # print(result)

    t1 = time.perf_counter()
    print(f'Время работы: {t1 - t0}')
