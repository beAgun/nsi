import io
import os
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pprint import pprint
import lxml
from lxml import etree
from nsi_parsing import *


from settings import DATABASE_CONFIG
DATABASE_URI = f"{DATABASE_CONFIG['engine']}://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}?charset={DATABASE_CONFIG['charset']}"

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

class RefBook:

    def __init__(self, kwargs, tag, namespace, path=None, etalon=False):
        self.tag = tag
        self.namespace = namespace
        self.code = kwargs.get('code')
        self.codeSystem = kwargs.get('codeSystem')
        self.codeSystemVersion = kwargs.get('codeSystemVersion')
        self.codeSystemName = kwargs.get('codeSystemName')
        self.displayName = kwargs.get('displayName')
        self.etalon = etalon
        self.path = path

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


def get_xml_doc(path: str):
    example_path = os.path.join(path)
    with io.open(example_path, "rb") as f:
        document_example = f.read()

    return document_example


def get_elements_by_name(parent_element, elem_namespace, elem_name: str, ns: dict, elem_cls, parents, etalon=False):

    elems = parent_element.xpath(f'//{elem_namespace}:' + f'{elem_name}', namespaces=ns)
    elems_attrib = []
    for i, elem in enumerate(elems):
        elem.attrib['path'] = find_ancestors(elem, parents)[1]
        elems_attrib += [elem_cls(elem.attrib, etalon)]
        if elem.attrib.get('codeSystem') is None:
            print(f'{i} {elem_name} is None')
            ancestors = find_ancestors(elem, parents)

    return elems_attrib


def get_elements_by_attribute(xml_tree, attr_name: str):
    elements = []
    for elem in xml_tree.iter():
        if attr_name in elem.attrib:
            elements += [elem]
    return elements


def get_only_elem_name(element):
    if isinstance(element, lxml.etree._Comment):
        return element.text
    if isinstance(element, lxml.etree._Element):
        return str(re.sub('{.*}', '', str(element.tag)))


def get_namespace(element):
    if isinstance(element, lxml.etree._Element):
        match = re.search('{(.*?)}', element.tag)
        if match:
            if match.group(1) != 'urn:hl7-org:v3':
                return match.group(1)
            else:
                return 'ns'


def find_ancestors(element, parents: dict):
    ancestors = []
    path = [get_only_elem_name(element)]
    element_set = (id(element), element)
    while element_set is not None:
        element_set = parents.get(element_set)
        if element_set is not None:
            element = element_set[1]
            ancestors += [element]
            path[-1] += f'[{element_set[2]}]'
            path += [get_only_elem_name(element)]
            element_set = (element_set[0], element_set[1])

    return ancestors, '/'.join(reversed(path))


def get_parent_map(tree):
    parent_map = {}
    for parent in tree.iter():
        cnt_number_of_elements = {get_only_elem_name(child): 1 for child in parent}

        for child_number, child in enumerate(child for child in parent):
            parent_map[(id(child), child)] = (id(parent), parent, cnt_number_of_elements[get_only_elem_name(child)])
            cnt_number_of_elements[get_only_elem_name(child)] += 1

    return parent_map


def compare_ref_books_names(elements, key_code=None, key_name=None):

    def find_name(record, cnt_right, cnt_found_matching, ans, found_matching, key_code, key_code_name_array):
        for key_name, name in record.items():
            name = str(name)
            if el.displayName.strip() == name:
                cnt_right += 1
                print('*' * 50, 'OK', '*' * 50)
                # print(key_code, key_name)
                key_code_name_array += [(key_code, key_name)]
                found_matching = 1
                any_found_matching = 1
                cnt_found_matching += 1
            else:
                ans_record = "\n".join(f'{key}: {val}' for key, val in record.items())
                ans_el = "\n".join(f'{key}: {val}' for key, val in el.__dict__.items())
                ans += [f'Не совпадают имена:\nrecord:\n{ans_record}\n\nelement:\n{ans_el}\n']

        return cnt_right, cnt_found_matching, ans, found_matching, cnt_found_matching, key_code_name_array

    cnt_right = 0
    cnt_found_matching = 0
    i = 0

    request_handler = RequestHandler(verify_ssl=False)
    nsi_client = NSIClient(request_handler)

    for el in elements:
        i += 1
        print('-' * 100 + str(i) + '-' * 100)

        add_oids = nsi_client.get_additional_oids(identifier=el.codeSystem)
        print(f'In doc: {el.codeSystem}', add_oids)

        all_ans = []
        any_found_matching = 0
        for oid in add_oids:
            link = nsi_client.get_link_download_reference_book(identifier=oid, version=el.codeSystemVersion)
            if not link:
                print(f'No link for {oid}, {el.codeSystemVersion}')
                continue
            print(f'found {oid}, {el.codeSystemVersion}')
            res = nsi_client.extract_and_load_json(link)

            found = 0
            found_matching = 0
            ans = []
            key_code_name_array = []

            print(res['records'][0])
            for record in res.get('records'):

                for key_code, code in record.items():
                    code = str(code)
                    if el.code == code:
                        found = 1

                        cnt_right, cnt_found_matching, ans, found_matching, cnt_found_matching, key_code_name_array = (
                            find_name(record, cnt_right, cnt_found_matching, ans, found_matching, key_code, key_code_name_array))

                        data = record.get('data')
                        if data:
                            cnt_right, cnt_found_matching, ans, found_matching, cnt_found_matching, key_code_name_array = (
                                find_name(data, cnt_right, cnt_found_matching, ans, found_matching, key_code, key_code_name_array))

                data = record.get('data')
                if data:
                    for key_code, code in data.items():
                        code = str(code)
                        if el.code == code:
                            found = 1

                            cnt_right, cnt_found_matching, ans, found_matching, cnt_found_matching, key_code_name_array = (
                                find_name(record, cnt_right, cnt_found_matching, ans, found_matching, key_code, key_code_name_array))

                            data = record.get('data')
                            if data:
                                cnt_right, cnt_found_matching, ans, found_matching, cnt_found_matching, key_code_name_array = (
                                    find_name(data, cnt_right, cnt_found_matching, ans, found_matching, key_code, key_code_name_array))

            if not found:
                print(f'Нет record c ключом {el.code}, codeSystem: {el.codeSystem}, version: {el.codeSystemVersion}')
            elif not found_matching:
                # print(*ans, sep='\n\n')
                all_ans += ans

            if found:
                stmt1 = """
                SELECT COUNT(*) from NSI_Mapping WHERE OID = '{oid}' AND version = '{version}'
                """.format(oid=el.codeSystem, version=el.codeSystemVersion)
                res = None

                res2 = None
                if el.codeSystem != oid:
                    stmt2 = """
                    SELECT COUNT(*) from NSI_Mapping WHERE OID = '{oid}' AND version = '{version}'
                    """.format(oid=oid, version=el.codeSystemVersion)


                try:
                    res = int(session.execute(stmt1).fetchone()[0])
                    if el.codeSystem != oid:
                        res2 = int(session.execute(stmt2).fetchone()[0])
                except Exception as e:
                    print('exc: ', e)
                if (res and el.codeSystem == oid) or (el.codeSystem != oid and res and res2):
                    print('already exists', res, res2 if el.codeSystem != oid else '-')
                    continue
                else:
                    print("don't exist", res, res2 if el.codeSystem != oid else '-')

                if len(key_code_name_array) > 1:
                    for i, val in enumerate(key_code_name_array):
                        print(f'{i + 1}) {val}')
                    option = int(input("Какой из вариантов занести в таблицу?  "))
                else:
                    option = 1

                key_code, key_name = key_code_name_array[option - 1]

                stmt1 = """
                INSERT into NSI_Mapping (OID, version, code_column_name, name_column_name, additional_oid) 
                VALUES ('{oid}', '{version}', '{code_column_name}', '{name_column_name}', '{additional_oid}');
                """
                stmt2 = """
                INSERT into NSI_Mapping (OID, version, code_column_name, name_column_name) 
                VALUES ('{oid}', '{version}', '{code_column_name}', '{name_column_name}');
                """

                stmt2 = stmt2.format(oid=oid, version=el.codeSystemVersion,
                                     code_column_name=key_code, name_column_name=key_name)

                try:
                    print('execute stmt2')
                    # print(stmt2)
                    res2 = session.execute(stmt2).rowcount
                    session.commit()
                    print(res2)
                except Exception as e:
                    print(e)

                if oid != el.codeSystem:

                    stmt1 = stmt1.format(oid=el.codeSystem, version=el.codeSystemVersion,
                                         code_column_name=key_code, name_column_name=key_name,
                                         additional_oid=oid)

                    try:
                        print('execute stmt1')
                        # print(stmt1)
                        res1 = session.execute(stmt1).rowcount
                        session.commit()
                        print(res1)
                    except Exception as e:
                        print(e)


        if not any_found_matching:
            print(*all_ans, sep='\n\n')
        print('-' * 100 + str(i) + '-' * 100 + '\n\n\n')

    print(f'Всего элементов с атрибутами (code, codeSystem, codeSystemVersion, displayName) в xml: {len(elements)}, '
          f'всего правильно указанных атрибутов displayName: {cnt_found_matching}')


def get_ref_book_elements_by_attribute(xml_path, attribute):

    xml_data = get_xml_doc(xml_path)
    tree = etree.fromstring(xml_data)
    parent_map = get_parent_map(tree)

    RefBook_elements = []
    OIDs = tuple()
    lxml_elements = get_elements_by_attribute(tree, attribute)

    for el in lxml_elements:
        rb_el = RefBook(el.attrib, get_only_elem_name(el), get_namespace(el), find_ancestors(el, parent_map)[1])

        if rb_el.codeSystem and rb_el.code and rb_el.codeSystemVersion and rb_el.displayName:
            RefBook_elements += [rb_el]
            OIDs += (rb_el.codeSystem,)

    return RefBook_elements


if __name__ == "__main__":
    t0 = time.perf_counter()

    dir = '/check_semd_error/nsi_validation/xml_files'
    for root, dirs, files in os.walk(dir):
        for file in files:
            path = os.path.join(root, file)
            print(path)
            # задать path
            try:
                elements = get_ref_book_elements_by_attribute(xml_path=path,
                                                          attribute='codeSystem')
                compare_ref_books_names(elements=elements)
            except Exception as e:
                print(e)

    t1 = time.perf_counter()
    print(f'Время работы: {t1 - t0}')