# TODO: in new-styled returns check types to capitalize
# TODO: if docs are short-line, delete \n
import inspect
import re
import mock
from pathlib import Path

import google.cloud.bigquery
import google.cloud.bigquery.dbapi

ARG_TYPE = re.compile(r":type[\s]+(?P<arg_name>[\S]+):[\s\n]+(?P<arg_type>[\S\s]+)")
PARAM = re.compile(r":param[\s]+([\S]+):(?P<arg_docs>[\S\s]+)")

RETURNS_TYPE = re.compile(r":rtype:[\s\n]+(?P<rtype>[\S\s]+)")
RETURNS_DOCS = re.compile(r":returns:(?P<rdocs>[\S\s]+)")

RAISES = re.compile(r":raises:[\s\n]+(?P<raises>[\S\s]+)")

SPACES = re.compile(r"(?P<spaces>[\s]+):param")
RSPACES = re.compile(r"\n+(?P<spaces>[\s]+):rtype")
RETURN_SPACES = re.compile(r"\n+(?P<spaces>[\s]+):raises:")

ARG_TYPE_NAME = re.compile(r"\((?P<arg_type_name>[\S]+)\):")
CLASS_STATEMENT = re.compile(r":class:`[~]?(?P<class_name>[\S\d]+)`")
EXC_STATEMENT = re.compile(r":exc:`[~]?(?P<exc_name>[\S\d]+)`")

NEW_TYPE_STATEMENT = re.compile(r"\n[\s]+[\S]+ \((?P<arg_type>[^)]+)")
OR_STATEMENT = re.compile(r"[\w\.`,\s]+or[\s]+[\w\.`]+")

LIST_OF_STATEMENT = re.compile(r"list of[\s\S\.`,\n]+")
# TUPLE_OF_STATEMENT = re.compile(r"tuple of[\s\S\.`,\n]+")
TUPLE_OF_STATEMENT = re.compile(r"tuple of")

NUM_SPACES = {"func": " " * 4, "method": " " * 8}
TYPES_TO_CAP = (
    "dict",
    "list",
    "tuple",
    "iterable",
    "set",
    "sequence",
    "iterator",
    "any",
)
CONTAINERS = ("Tuple", "Dict", "Sequence", "List")

processed_objects = []


def write_to_file(old, new, addr):
    if old and new and old != new:
        if "\n\n\n" in new:
            new = new.replace("\n\n\n", "\n\n")

        with open(addr, "r") as file:
            lines = file.read()

        lines = lines.replace(old, new)
        with open(addr, "w") as file:
            file.write(lines)


def del_last_points(docs):
    while docs[-1] == ".":
        docs = docs[:-1]
    return docs


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


def delete_line(docs, contains):
    parts = docs.split(contains + "\n")
    return parts[0] + parts[1].lstrip()


def designate_exc_types(rdocs):
    exc_types = []
    groups = []

    exc_match_iter = EXC_STATEMENT.finditer(rdocs)
    for match in exc_match_iter:
        groups.append(match.group(0))
        exc_types.append(match.group("exc_name"))

    class_match_iter = CLASS_STATEMENT.finditer(rdocs)
    for match in class_match_iter:
        class_name = match.group("class_name")
        if "error" in class_name.lower():
            groups.append(match.group(0))
            exc_types.append(match.group("class_name"))

    if not len(groups) > 1:
        for group in groups:
            rdocs = rdocs.replace(group, "")

    return exc_types, rdocs.lstrip()


def format_params(docs, num, type_, addr):
    match_type, type_statement = get_indexes(docs, ":type ", ":param ", ARG_TYPE)
    match_param, param_statement = get_indexes(docs, ":param ", "\n\n", PARAM)

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

        docs = delete_line(docs, type_statement)

        arg_type = del_last_points(
            capitalize_type(del_class_statements(match_type.group("arg_type")))
        )

        new_param = "{title}    {name} ({type_}):{docs}".format(
            title="Args:\n" + NUM_SPACES[type_] if num == 0 else "",
            name=match_type.group("arg_name"),
            type_=arg_type,
            docs=arg_docs,
        )

        docs = docs.replace(param_statement, new_param)

    return docs


def format_raises(docs, type_):
    match, raises_statement = get_indexes(docs, ":raises:", "$", RAISES)

    if match is not None:
        rdocs = match.group("raises")
        exc_types, rdocs = designate_exc_types(rdocs)

        if "\n" in rdocs:
            if not rdocs.startswith("\n"):
                spaces = RETURN_SPACES.search(docs).group("spaces") + " " * 4
            else:
                rdocs = rdocs[1:]
                spaces = " " * (len(rdocs) - len(rdocs.lstrip()))

            rdocs = add_spaces(rdocs, spaces)
        else:
            rdocs = " " + rdocs.lstrip()

        new_raises = "Raises:\n{spaces}    {type_}:{docs}".format(
            spaces=NUM_SPACES[type_], docs=rdocs, type_=", ".join(exc_types)
        )
        docs = docs.replace(raises_statement, new_raises)

    return docs


def format_returns(docs, type_, addr):
    match_type, type_statement = get_indexes(docs, ":rtype", ":returns:", RETURNS_TYPE)
    match_return, old_return = get_indexes(
        docs, ":returns:", "Raises:", RETURNS_DOCS
    )

    if match_return is not None and match_type is not None:
        rdocs = match_return.group("rdocs")

        if "\n" in rdocs:
            if not rdocs.startswith("\n"):
                spaces = RSPACES.search(docs).group("spaces") + " " * 4
            else:
                rdocs = rdocs[1:]
                spaces = " " * (len(rdocs) - len(rdocs.lstrip()))

            rdocs = add_spaces(rdocs, spaces)
        else:
            rdocs = " " + rdocs.lstrip()

        docs = delete_line(docs, type_statement)

        rtype = del_last_points(
            capitalize_type(del_class_statements(match_type.group("rtype")))
        )

        new_return = "Returns:\n{spaces}    {type_}:{docs}".format(
            spaces=NUM_SPACES[type_], type_=rtype, docs=rdocs
        )

        if "Raises:" in docs:
            new_return += "\n"

        docs = docs.replace(old_return, new_return)

    return docs


def full_class_path(class_name):
    addr = path = ""
    if class_name.startswith("."):
        class_name = class_name.split(".")[-1]

        for key in codes:
            if "class " + class_name in codes[key]:
                addr = str(key)

        if addr:
            path = (
                addr[addr.index("\google\cloud") + 1 : -3].replace("\\", ".") + "."
            )

    return path, class_name


def del_class_statements(docs):
    path = ""
    match_iter = CLASS_STATEMENT.finditer(docs)

    for match in match_iter:
        class_name = match.group("class_name")
        path, class_name = full_class_path(class_name)
        docs = docs.replace(match.group(0), path + class_name)

    path, class_name_new = full_class_path(docs)
    docs = docs.replace(docs, path + class_name_new)

    return docs


def capitalize_type(type_def):
    type_def = del_last_points(type_def)

    for name in TYPES_TO_CAP:
        if type_def == name:
            type_def = type_def.capitalize()
        else:
            pattern = re.compile("[\W]+" + name + "[\W]+")
            match_iter = pattern.finditer(type_def)
            for match in match_iter:
                found = match.group(0)
                found = found.replace(name, name.capitalize())
                type_def = type_def.replace(match.group(0), found)

    for cont in CONTAINERS:
        if cont + " of " in type_def:
            type_def = type_def.replace(" of ", "[")
            type_def += "]"

    match = OR_STATEMENT.match(type_def)
    if not match is None:
        or_statement = match.group(0)
        if ", or" in or_statement:
            sep = ""
        elif " or\n" in or_statement:
            sep = ", "
        elif " or " in or_statement:
            sep = ","

        union_statement = "Union[" + or_statement.replace(" or", sep) + "]"
        type_def = type_def.replace(or_statement, union_statement)

    match = LIST_OF_STATEMENT.match(type_def)
    if match is not None:
        old = match.group(0)
        new = "List[" + old.split(" of")[-1].lstrip() + "]"
        type_def = type_def.replace(old, new)

    match2 = TUPLE_OF_STATEMENT.match(type_def)
    if match2 is not None:
        old = match2.group(0)
        new = "Tuple[" + old.split(" of")[-1].lstrip() + "]"
        type_def = type_def.replace(old, new)

    if "None" in type_def and "Union" in type_def:
        type_def = type_def.replace("Union", "Optional")
        type_def = type_def.split(sep)[0] + "]"

    return type_def


def replacements_for_args(docs, type_, addr):
    for num in range(docs.count(":type ")):
        docs = format_params(docs, num, type_, addr)

    if ":raises:" in docs:
        docs = format_raises(docs, type_)

    if ":returns:" in docs:
        docs = format_returns(docs, type_, addr)

    match_iter = ARG_TYPE_NAME.finditer(docs)
    for match in match_iter:
        name = capitalize_type(match.group("arg_type_name"))
        docs = docs.replace(match.group(0), "(" + name + "):")

    match_iter = NEW_TYPE_STATEMENT.finditer(docs)
    for match in match_iter:
        old_group = match.group(0)
        arg_type_old = match.group("arg_type")
        new_group = old_group.replace(arg_type_old, del_class_statements(arg_type_old))
        docs = docs.replace(old_group, new_group)

    return docs


def untouched(docs):
    """Function to override inspect.cleandoc() to avoid docs formating."""
    return docs


def rewrite_docs(docs, type_, addr):
    new = replacements_for_args(docs, type_, addr)
    write_to_file(docs, new, addr)


def process_members(obj):
    for name, member in inspect.getmembers(obj):
        # skip processed members and builtins
        if member in processed_objects or name.startswith("__"):
            continue

        # skip compiled modules
        try:
            addr = inspect.getsourcefile(member)
        except TypeError:
            continue

        if "google\cloud" not in addr:  # process only Google modules
            continue

        is_method = inspect.ismethod(member) or isinstance(member, property)

        docs = inspect.getdoc(member)
        if not docs:  # skip, if no docs on member
            continue

        if is_method or inspect.isfunction(member):
            if not is_method:  # kludge: some methods somehow have type "function"
                is_method = "self" in inspect.getfullargspec(member).args

            type_ = "method" if is_method else "func"
            rewrite_docs(docs, type_, addr)

        elif inspect.isclass(member) or inspect.ismodule(member):
            if inspect.isclass(member):
                rewrite_docs(docs, "func", addr)

            process_members(member)

        processed_objects.append(obj)


codes = {}
for filename in Path(
    r"C:/Users/ubc/AppData/Local/Programs/Python/Python37-32/Lib/site-packages/google/cloud/bigquery"
).glob("**/*.py"):
    with open(filename, "r") as file:
        codes[filename] = file.read()

# disabling inspect docs formating
with mock.patch("inspect.cleandoc", side_effect=untouched):
    process_members(google.cloud.bigquery)
    process_members(google.cloud.bigquery.dbapi)
