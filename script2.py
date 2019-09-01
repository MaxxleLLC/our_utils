import inspect
import re
import google.cloud.bigquery
import google.cloud.bigquery.dbapi
import mock

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

NUM_SPACES = {"func": " " * 4, "method": " " * 8}

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


def format_params(docs, num, type_):
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

        new_param = "{title}    {name} ({type_}):{docs}".format(
            title="Args:\n" + NUM_SPACES[type_] if num == 0 else "",
            name=match_type.group("arg_name"),
            type_=match_type.group("arg_type"),
            docs=arg_docs,
        )

        docs = docs.replace(param_statement, new_param)

    return docs


def format_raises(docs, type_):
    match, raises_statement = get_indexes(docs, ":raises:", "$", RAISES)

    if match is not None:
        rdocs = match.group("raises")

        if "\n" in rdocs:
            if not rdocs.startswith("\n"):
                spaces = RETURN_SPACES.search(docs).group("spaces")
            else:
                rdocs = rdocs[1:]
                spaces = " " * (len(rdocs) - len(rdocs.lstrip()))

            rdocs = add_spaces(rdocs, spaces)
        else:
            rdocs = " " + rdocs.lstrip()

        new_raises = "Raises:{docs}".format(spaces=NUM_SPACES[type_], docs=rdocs)
        docs = docs.replace(raises_statement, new_raises)

    return docs


def format_returns(docs, type_):
    match_type, type_statement = get_indexes(docs, ":rtype", ":returns:", RETURNS_TYPE)
    match_param, param_statement = get_indexes(
        docs, ":returns:", "Raises:", RETURNS_DOCS
    )

    if match_param is not None and match_type is not None:
        rdocs = match_param.group("rdocs")

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

        new_return = "Returns:\n{spaces}    ({type_}):{docs}".format(
            spaces=NUM_SPACES[type_], type_=match_type.group("rtype"), docs=rdocs
        )

        if "Raises:" in docs:
            new_return += "\n"

        docs = docs.replace(param_statement, new_return)

    return docs


def replacements_for_args(docs, type_):
    rold = docs
    for num in range(docs.count(":type ")):
        docs = format_params(docs, num, type_)

    if ":raises:" in docs:
        docs = format_raises(docs, type_)

    if ":returns:" in docs:
        docs = format_returns(docs, type_)

    match_iter = ARG_TYPE_NAME.finditer(docs)
    for match in match_iter:
        name = match.group("arg_type_name")
        if name in ("dict", "list", "tuple", "iterable", "set", "sequence", "iterator"):
            name = name.capitalize()

        docs = docs.replace(match.group(0), "(" + name + "):")

    match_iter = CLASS_STATEMENT.finditer(docs)
    for match in match_iter:
        docs = docs.replace(match.group(0), match.group("class_name"))

    return rold, docs


def untouched(docs):
    """Function to override inspect.cleandoc() to avoid docs formating."""
    return docs


def rewrite_docs(docs, type_, addr):
    if docs:
        old, new = replacements_for_args(docs, type_)
        if new and old:
            write_to_file(old, new, addr)


def process_members(obj):
    # disabling inspect docs formating
    with mock.patch("inspect.cleandoc", side_effect=untouched):
        for name, member in inspect.getmembers(obj):
            # skip processed members and builtins
            if member in processed_objects or name.startswith("__"):
                continue

            try:
                addr = inspect.getsourcefile(member)
            except TypeError:
                continue

            if "google\cloud" not in addr:  # process only Google modules
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
