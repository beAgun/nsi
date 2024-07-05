import io
import os
import re
import time
from functools import wraps
import lxml
from colorama import Fore, Style
from lxml.etree import _Element, _Comment
from nsi_validation.config import USE_TIMER

ACC = 0


def timer(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        global ACC
        t0 = time.perf_counter()
        res = f(*args, **kwargs)
        t1 = time.perf_counter()
        print(f'{Fore.LIGHTBLACK_EX}Время работы {f.__name__}: {t1 - t0}{Style.RESET_ALL}')
        ACC += t1 - t0
        return res

    return wrapper if USE_TIMER else f


@timer
def get_xml_doc(path: str):
    example_path = os.path.join(path)
    with io.open(example_path, "rb") as f:
        document_example = f.read()

    return document_example


@timer
def get_tag(element):
    if isinstance(element, _Element):
        return str(re.sub('{.*}', '', str(element.tag)))
    raise TypeError('Not lxml.etree._Element type')


@timer
def get_comment_text(element):
    if isinstance(element, _Comment):
        return element.text
    raise TypeError('Not lxml.etree._Comment type')


@timer
def get_namespace(element):
    if isinstance(element, lxml.etree._Element):
        match = re.search('{(.*?)}', element.tag)
        if match:
            if match.group(1) != 'urn:hl7-org:v3':
                return match.group(1)
            else:
                return 'ns'


@timer
def get_parent_map(tree):
    parent_map = {}
    for parent in tree.iter():
        cnt_number_of_elements = {get_tag(child): 1 for child in parent}

        for child_number, child in enumerate(child for child in parent):
            parent_map[(id(child), child)] = (id(parent), parent, cnt_number_of_elements[get_tag(child)])
            cnt_number_of_elements[get_tag(child)] += 1

    return parent_map


@timer
def find_ancestors(element, parents: dict):
    ancestors = []
    path = [get_tag(element)]
    element_set = (id(element), element)
    while element_set is not None:
        element_set = parents.get(element_set)
        if element_set is not None:
            element = element_set[1]
            ancestors += [element]
            path[-1] += f'[{element_set[2]}]'
            path += [get_tag(element)]
            element_set = (element_set[0], element_set[1])

    return '/'.join(reversed(path))