import inspect
import re
import google.cloud.bigquery
import google.cloud.bigquery.dbapi
import mock

OLD_TYPE = re.compile(r":type[\s]+(?P<arg_name>[\S]+):[\s\n]+(?P<arg_type>[\S\s]+)")
OLD_PARAM = re.compile(r":param[\s]+([\S]+):(?P<arg_docs>[\S\s]+)")
SPACES = re.compile(r"(?P<spaces>[\s]+):param")

NUM_SPACES = {"func": " " * 4, "method": " " * 8}

processed_objects = []


def write_to_file(old, new, addr):
    if old and new and old != new:
        with open(addr, "r") as file:
            lines = file.read()

        lines = lines.replace(old, new)
        with open(addr, "w") as file:
            file.write(lines)


def add_spaces(docs, spaces):
    docs = docs.split("\n")
    for index, line in enumerate(docs):
        if line:
            docs[index] = spaces + " " * 4 + line.lstrip()

    docs = "\n" + "\n".join(docs)
    return docs


def get_indexes(string, start, end, temp):
    start_ind = string.index(start)
    if end in string[start_ind:]:
        end_ind = string.index(end, start_ind)
    else:
        end_ind = len(string) - 1

    string = strip_n_news(string[start_ind:end_ind])
    return temp.search(string), string


def strip_n_news(string):
    string = string.rstrip()
    if string[-1] == "\n":
        string = string[:-1]
    return string


def format_docs(docs, tag, num, type_):
    if tag == ":type ":
        match_type, type_statement = get_indexes(docs, tag, ":param ", OLD_TYPE)
        match_param, param_statement = get_indexes(docs, ":param ", "\n\n", OLD_PARAM)

        if match_param is not None and match_type is not None:
            arg_docs = match_param.group("arg_docs")
            if "\n" in arg_docs:
                if not arg_docs.startswith("\n"):
                    spaces = SPACES.search(docs).group("spaces")[1:] + " " * 4
                else:
                    arg_docs = arg_docs[1:]
                    spaces = " " * (len(arg_docs) - len(arg_docs.lstrip()))

                arg_docs = add_spaces(arg_docs, spaces)
            else:
                arg_docs = " " + arg_docs.lstrip()

            parts = docs.split(type_statement + "\n")
            docs = parts[0] + parts[1].lstrip()

            new_param = "{title}    {name} ({type_}):{docs}".format(
                title="Args:\n" + NUM_SPACES[type_] if num == 0 else "",
                name=match_type.group("arg_name"),
                type_=match_type.group("arg_type"),
                docs=arg_docs,
            )

            docs = docs.replace(param_statement, new_param)

    return docs


def replacements_for_args(docs, type_):
    rold = docs
    for tag in (":type ",):
        for num in range(docs.count(tag)):
            docs = format_docs(docs, tag, num, type_)
    return rold, docs


def untouched(docs):
    return docs


def rewrite_docs(docs, type_, addr):
    if docs:
        old, new = replacements_for_args(docs, type_)
        if new and old:
            write_to_file(old, new, addr)


def process_members(obj):
    with mock.patch("inspect.cleandoc", side_effect=untouched):
        for name, member in inspect.getmembers(obj):
            if member in processed_objects or name.startswith("__"):
                continue

            try:
                addr = inspect.getsourcefile(member)
            except TypeError:
                continue

            if "google\cloud" not in addr:
                continue

            is_method = inspect.ismethod(member) or isinstance(member, property)
            is_func = inspect.isfunction(member)
            docs = inspect.getdoc(member)

            if is_method or is_func:
                if not is_method:
                    is_method = "self" in inspect.getfullargspec(member).args

                type_ = "method" if is_method else "func"
                rewrite_docs(docs, type_, addr)

            elif inspect.isclass(member) or inspect.ismodule(member):
                if inspect.isclass(member):
                    rewrite_docs(docs, "func", addr)

                process_members(member)

            processed_objects.append(obj)


process_members(google.cloud.bigquery)
process_members(google.cloud.bigquery.dbapi)
