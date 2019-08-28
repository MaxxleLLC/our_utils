import inspect
import re
import bigquery.google.cloud.bigquery


OLD_TYPES = re.compile(
    r"""
    :type[\s]+(?P<arg_name>[\S]+):[\s\n]+(?P<arg_type>[\S\s]+)\n
    :param[\s]+[\S]+:[\s\n]+(?P<arg_doc>[\s\S]+)\n
    :rtype:(?P<rtype>[\s\S\n]+)\n
    :returns:(?P<returns>[\s\S\n]+)\n
    :raises:(?P<raises>[\s\S\n]+)
    """,
    re.VERBOSE
)

def check_old_types(docs):
    if ':type' in docs:
        print('docs: ')
        print(docs)
        print('++++++++')
        match = OLD_TYPES.search(docs)
        if match is not None:
            print('regex_name: ', match.group("arg_name"))
            print()
            print('regex_type: ', match.group("arg_type"))
            print()
            print('regex_doc: ')
            print(match.group("arg_doc"))
            print()
            print('regex_raises: ')
            print(match.group("raises"))
            print()
            print('rtype: ')
            print(match.group("rtype"))
            print()
            print('returns: ')
            print(match.group("returns"))

        print('#############')


def process_members(obj):
    for name, member in inspect.getmembers(obj):
        if name.startswith('__'):
            continue

        if inspect.isfunction(member):
            docs = inspect.getdoc(member)
            # print('func: ', name)
            # print('docs: ')
            # print(docs)
        elif inspect.ismethod(member):
            docs = inspect.getdoc(member)
            print('method: ', name)
            if docs:# and name == 'positional':
                check_old_types(docs)
        elif inspect.isclass(member):
            docs = inspect.getdoc(member)
            print('class: ', name)
            # print('docs: ')
            # print(docs)

            process_members(member)

        print('--------------')


process_members(bigquery.google.cloud.bigquery)