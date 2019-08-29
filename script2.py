import inspect
import re
import google.cloud.bigquery
import google.cloud.bigquery.dbapi
import mock

SPACES = {"method": "        ", "func": "    "}

OLD_TYPE = re.compile(r':type[\s]+(?P<arg_name>[\S]+):[\s\n]+(?P<arg_type>[\S\s]+)')
OLD_PARAM = re.compile(r':param[\s]+([\S]+):[\s\n]+(?P<arg_docs>[\S\s]+)')

processed_objects = []


def write_to_file(old, new, addr):
    if old and new and old != new:
        file = open(addr, "r")
        lines = file.read()
        file.close()
        # if ':type size: int' in old:
            # print(addr)
            # print(repr(old))
            # print('------------------')
            # print(repr(lines))
        lines = lines.replace(old, new)
        file = open(addr, "w")
        file.write(lines)
        file.close()


def add_spaces(old_string, type_):
    old_strings = old_string.split("\n")
    for index, string in enumerate(old_strings):
        if string != '':
            old_strings[index] = SPACES[type_] + string
        else:
            old_strings[index] = string

    new_string = "\n".join(old_strings)
    new_string = new_string.lstrip()
    return new_string


def get_indexes(string, start, end):
    start_ind = string.index(start)
    if not end in string[start_ind:]:
        end_ind = len(string) - 1
    else:
        end_ind = string.index(end, start_ind)
    return start_ind, end_ind


def format_docs(docs, tag):
    if tag == ":type ":
        type_start, type_end = get_indexes(docs, tag, ":param ")

        type_statement = docs[type_start: type_end].rstrip()
        if type_statement[-1] == '\n':
            type_statement = type_statement[:-1]
        # print('---------------------------')
        # print(type_statement)
        match_type = OLD_TYPE.search(type_statement)
        # print(match_type.group('arg_name'))
        # print(match_type.group('arg_type'))

        type_start, type_end = get_indexes(docs, ":param ", "\n\n")
        param_statement = docs[type_start: type_end].rstrip()
        if param_statement[-1] == '\n':
            param_statement = param_statement[:-1]
        match_param = OLD_PARAM.search(param_statement)
        # print(match_param.group("arg_docs"))

        # print('################################')
        if match_param is not None and match_type is not None:
            docs = docs.replace(type_statement + '\n', '')
            new_param = "{name} ({type_}): {docs}\n".format(
                name=match_type.group('arg_name'),
                type_=match_type.group('arg_type'),
                docs=match_param.group("arg_docs")
            )

            docs = docs.replace(param_statement + '\n', new_param)
        # print(docs)

    return docs


def replacements_for_args(docs, type_):
    rold = docs

    for tag in (":type ",):#, ":rtype:", ":raises:"):
        for i in range(docs.count(tag)):
            docs = format_docs(docs, tag)
            # print(docs)

    # rold = add_spaces(rold, type_)
    # docs = add_spaces(docs, type_)
    return rold, docs


def untouched(docs):
    return docs


def process_members(obj):
    with mock.patch('inspect.cleandoc', side_effect=untouched):
        for name, member in inspect.getmembers(obj):
            if member in processed_objects or name.startswith("__"):
                continue

            try:
                addr = inspect.getsourcefile(obj)
            except TypeError:
                continue

            if "bigquery" not in addr:
                continue

            is_method = inspect.ismethod(member) or isinstance(member, property)
            is_func = inspect.isfunction(member)

            if is_method or is_func:
                if not is_method:
                    is_method = 'self' in inspect.getfullargspec(member).args
                docs = inspect.getdoc(member)
                if docs:
                    type_ = "method" if is_method else "func"
                    old, new = replacements_for_args(docs, type_)
                    if new and old:
                        write_to_file(old, new, addr)

            elif inspect.isclass(member) or inspect.ismodule(member):
                if inspect.isclass(member):
                    docs = inspect.getdoc(member)
                    if docs:
                        if name == 'LoadJob':
                            print()
                        old, new = replacements_for_args(docs, "func")
                        if new and old:
                            write_to_file(old, new, addr)

                process_members(member)

            processed_objects.append(obj)


process_members(google.cloud.bigquery)
process_members(google.cloud.bigquery.dbapi)
