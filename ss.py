import codecs
import subprocess

LICENSE = """
// Copyright 2019 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
"""


def is_func(line):
    return line.startswith("func ") and ("error" in line)


directory = (
    r"C:/go_wd/src/github.com/GoogleCloudPlatform/golang-samples/storage/objects/"
)
filename = directory + r"main.go"

with codecs.open(filename, "r", "utf-8") as file:
    source_code = file.readlines()

    for index, line in enumerate(source_code):
        if is_func(line):
            cursor = source_code.index("}\r\n", index) + 1
            func_scode = source_code[index:cursor]
            name = source_code[index].split("(")[0].split()[1]

            for line in func_scode:
                if "[START" in line:
                    start_line = line

                if "[END" in line:
                    end_line = line

            func_scode.remove(start_line)
            func_scode.remove(end_line)

            func_code = "".join(func_scode)
            func_code = func_code.replace("\r", "")

            with open(directory + name + ".go", "w") as new_file:
                new_file.write(
                    LICENSE + "package objects\n\n" + start_line + "import (\n)\n\n"
                )
                new_file.write(func_code + end_line)


subprocess.call("goimports -w " + directory, shell=True)
