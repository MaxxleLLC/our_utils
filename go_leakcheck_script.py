from pathlib import Path
import codecs


def is_test(line):
    return line.startswith("func ") and (
        "t *testing.T" in line or "m *testing.M" in line
    )


for filename in Path(r"C:/go_wd/src/cloud.google.com/go").glob("**/*_test.go"):
    with codecs.open(filename, "r", "utf-8") as file:
        to_insert = []
        source_code = file.readlines()

        for index, line in enumerate(source_code):
            if is_test(line):
                cursor = source_code.index("}\r\n", index)
                skip_line = ""

                while line != source_code[cursor] and skip_line == "":
                    if "t.Skip(" in source_code[cursor]:
                        skip_ind = cursor
                        skip_line = source_code[cursor]
                        break
                    cursor -= 1

                ins_index = cursor + 1
                if skip_line:
                    ins_index = skip_ind + 1
                    if skip_line.startswith("\t\t"):
                        ins_index = skip_ind + 2

                to_insert.append(ins_index)

        for index in sorted(to_insert, reverse=True):
            var = "m" if "m *testing.M" in line else "t"
            source_code.insert(index, "\tdefer leakcheck.Check(" + var + ")\r\n")

    with codecs.open(filename, "w", "utf-8") as file:
        file.write("".join(source_code))
