import inspect
import re
import google.cloud.bigquery
import google.cloud.bigquery.dbapi

# :type[\s]+(?P<arg_name>[\S]+):
# [\s\n]+(?P<arg_type>[\S\s]+)
# (:raises:[\s]+(?P<raises>[\s\S\n]+))?
# :param[\s]+[\S]+:[\s\n]+(?P<arg_doc>[\S\s]+)

SPACES = {"method": "        ", "func": "    "}
OLD_RETURN = re.compile(
    r"""
    :rtype:[\s]+(?P<rtype>[\s\S\n]+)\n
    :returns:[\s]?(?P<returns>[^.$]+)($|.$)
    """,
    re.VERBOSE,
)

processed_objects = []


def write_to_file(old, new, addr):
    if old and new:
        file = open(addr, "r")
        lines = file.read()
        file.close()
        lines = lines.replace(old, new)
        file = open(addr, "w")
        file.write(lines)
        file.close()


def add_spaces(old_string, type_):
    old_string = old_string.split("\n")
    new_string = "\n".join([SPACES[type_] + line for line in old_string])
    return new_string


def replacements_for_args(docs, type_):
    rold = rnew = None
    if ":rtype" in docs:
        match = OLD_RETURN.search(docs)
        if match is not None:
            rold = match.group(0)

            rnew = """Returns:
    {rtype}: {return_doc}.""".format(
                rtype=match.group("rtype"), return_doc=match.group("returns")
            )
            rold = add_spaces(rold, type_)
            rnew = add_spaces(rnew, type_)

    return rold, rnew


def process_members(obj):
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
            docs = inspect.getdoc(member)
            if docs:
                type_ = "method" if is_method else "func"
                old, new = replacements_for_args(docs, type_)
                write_to_file(old, new, addr)

        elif inspect.isclass(member) or inspect.ismodule(member):
            process_members(member)

        processed_objects.append(obj)


process_members(google.cloud.bigquery)
process_members(google.cloud.bigquery.dbapi)
