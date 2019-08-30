import inspect
import re
import google.cloud.bigquery
import google.cloud.bigquery.dbapi
import mock

OLD_TYPE = re.compile(r":type[\s]+(?P<arg_name>[\S]+):[\s\n]+(?P<arg_type>[\S\s]+)")
OLD_PARAM = re.compile(r":param[\s]+([\S]+):[\s\n]+(?P<arg_docs>[\S\s]+)")

processed_objects = []


def write_to_file(old, new, addr):
    if old and new and old != new:
        with open(addr, "r") as file:
            lines = file.read()

        lines = lines.replace(old, new)
        with open(addr, "w") as file:
            file.write(lines)


def get_indexes(string, start, end):
    start_ind = string.index(start)
    if end in string[start_ind:]:
        end_ind = string.index(end, start_ind)
    else:
        end_ind = len(string) - 1
    return start_ind, end_ind


def strip_n_news(string):
    string = string.rstrip()
    if string[-1] == "\n":
        string = string[:-1]
    return string


def format_docs(docs, tag):
    if tag == ":type ":
        type_start, type_end = get_indexes(docs, tag, ":param ")
        type_statement = strip_n_news(docs[type_start:type_end])
        match_type = OLD_TYPE.search(type_statement)

        type_start, type_end = get_indexes(docs, ":param ", "\n\n")
        param_statement = strip_n_news(docs[type_start:type_end])
        match_param = OLD_PARAM.search(param_statement)

        if match_param is not None and match_type is not None:
            docs = docs.replace(type_statement + "\n", "")
            new_param = "{name} ({type_}): {docs}\n".format(
                name=match_type.group("arg_name"),
                type_=match_type.group("arg_type"),
                docs=match_param.group("arg_docs"),
            )

            docs = docs.replace(param_statement + "\n", new_param)

    return docs


def replacements_for_args(docs, type_):
    rold = docs
    for tag in (":type ",):
        for _ in range(docs.count(tag)):
            docs = format_docs(docs, tag)
    return rold, docs


def untouched(docs):
    return docs


def process_members(obj):
    with mock.patch("inspect.cleandoc", side_effect=untouched):
        for name, member in inspect.getmembers(obj):
            if member in processed_objects or name.startswith("__"):
                continue

            try:
                addr = inspect.getsourcefile(member)
            except TypeError:
                continue

            if "bigquery" not in addr:
                continue

            is_method = inspect.ismethod(member) or isinstance(member, property)
            is_func = inspect.isfunction(member)

            if is_method or is_func:
                if not is_method:
                    is_method = "self" in inspect.getfullargspec(member).args
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
                        old, new = replacements_for_args(docs, "func")
                        if new and old:
                            write_to_file(old, new, addr)

                process_members(member)

            processed_objects.append(obj)


process_members(google.cloud.bigquery)
process_members(google.cloud.bigquery.dbapi)
