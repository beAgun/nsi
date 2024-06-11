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

    cnt_right = 0
    cnt_found_matching = 0
    i = 0

    request_handler = RequestHandler(verify_ssl=False)
    nsi_client = NSIClient(request_handler)

    for el in elements:
        i += 1
        print('-' * 100 + str(i) + '-' * 100)

        add_oids = nsi_client.get_additional_oids(identifier=el.codeSystem)
        print(add_oids)

        for oid in add_oids:
            link = nsi_client.get_link_download_reference_book(identifier=oid, version=el.codeSystemVersion)
            if not link:
                continue
            print(f'found {oid}')
            res = nsi_client.extract_and_load_json(link)

            found = 0
            found_matching = 0
            ans = []

            for record in res.get('records'):
                if (el.code in map(str, record.values()) or
                        (el.code in map(str, record.get('data').values()) if record.get('data') else 0)):
                    found = 1
                    if (el.displayName.strip() in record.values() or
                            (el.displayName in map(str, record.get('data').values()) if record.get('data') else 0)):
                        cnt_right += 1
                        # print(f'совпадают имена: \n {el.displayName}')
                        # print(record)
                        print('*'*50, 'OK', '*'*50)
                        found_matching = 1
                        cnt_found_matching += 1
                    else:
                        ans_record = "\n".join(f'{key}: {val}' for key, val in record.items())
                        ans_el = "\n".join(f'{key}: {val}' for key, val in el.__dict__.items())
                        ans += [f'Не совпадают имена:\nrecord:\n{ans_record}\n\nelement:\n{ans_el}\n']

            if not found:
                print(f'Нет record c ключом {el.code}, codeSystem: {el.codeSystem}, version: {el.codeSystemVersion}')
            elif not found_matching:
                print(*ans, sep='\n\n')

        print('-' * 100 + str(i) + '-' * 100 + '\n\n\n')

    print(f'Всего элементов с атрибутами (code, codeSystem, codeSystemVersion, displayName) в xml: {len(elements)}, '
          f'всего правильно указанных атрибутов displayName: {cnt_found_matching}')


def get_RefBook_elements_by_attribute(xml_path, attribute):

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

    # задать path
    elements = get_RefBook_elements_by_attribute(xml_path='/home/vista/MyPycharmProjects/vista_scripts/nsi/ep89.xml',
                                                 attribute='codeSystem')
    compare_ref_books_names(elements=elements)

    t1 = time.perf_counter()
    print(f'Время работы: {t1 - t0}')