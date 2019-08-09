import inspect
import google.cloud.bigquery.docs.snippets as snippets

LICENSE = '''# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


'''

RST_DATASET = 'C:/git_reps/google-cloud-python/bigquery/docs/usage/datasets.rst'
RST_TABLES = 'C:/git_reps/google-cloud-python/bigquery/docs/usage/tables.rst'
SAMPLES_DIR = 'C:/git_reps/google-cloud-python/bigquery/samples/'


def write_test(file_name, name):
    with open(file_name, 'w') as test_file:
        test_file.write(LICENSE)
        test_file.write(
            'from .. import {}\n\n\n'.format(name[5:])
        )
        test_file.write(
            'def {}(capsys, client):'.format(name)
        )


def write_sample(file_name, object, rst_table_lines, rst_dataset_lines, code_deleted):
    code = inspect.getsource(object)
    code_deleted.append(code)

    # cut decorators
    code = code[code.index('def '):]

    # set START and END tags
    code = code.split('\n')
    for line in code:
        if 'START' in line:
            start = line
            name = line.split(' ')[6][:-1]
            end = '    # [END {name}]'.format(
                name=name
            )

    code.pop(code.index(start))
    if end in code:
        code.pop(code.index(end))
    code.insert(1, '\n' + start)
    code.append(end)

    # add license
    code = LICENSE + '\n'.join(code)
    code = code.replace('def test_', 'def ')

    # update dst marks
    found = False
    for index, line in enumerate(rst_table_lines):
        if name in line:
            rst_table_lines[index - 3] = rst_table_lines[index - 3].replace(
                'snippets.py', 'samples/' + file_name.split('/')[-1]
            )

            new_mark = rst_table_lines[index - 3].replace(
                'snippets.py', 'samples/' + file_name.split('/')[-1]
            )

            found = True
            break

    if not found:
        new_mark = [
            '\n',
            '[-REPLACE_COMMENT-]\n',
            ':func:`~google.cloud.bigquery.[-REPLACE_METHOD-]` method:\n',
            '\n',
            '.. literalinclude:: ../samples/' + 'samples/' + file_name.split('/')[-1] + '\n',
            '   :language: python\n',
            '   :dedent: 4\n',
            '   :start-after: [START {}]\n'.format(name),
            '   :end-before: [END {}]\n'.format(name),
        ]

        if 'dataset' in file_name:
            rst_dataset_lines += new_mark
        else:
            rst_table_lines += new_mark

    with open(file_name, 'w') as new_sample:
        new_sample.write(code)


def write_marks(file_name, lines):
    lines = ''.join(lines)
    with open(file_name, 'w') as file_:
        file_.write(lines)


code_deleted = []

with open(RST_DATASET, 'r') as file_:
    rst_dataset_lines = file_.readlines()

with open(RST_TABLES, 'r') as file_:
    rst_table_lines = file_.readlines()

for name, obj in inspect.getmembers(snippets):
    if inspect.isfunction(obj) and name.startswith('test_'):
        write_sample(
            SAMPLES_DIR + name[5:] + '.py',
            obj,
            rst_table_lines,
            rst_dataset_lines,
            code_deleted
        )

        write_test(
            SAMPLES_DIR + 'tests/' + name + '.py',
            name
        )


write_marks(RST_DATASET, rst_dataset_lines)
write_marks(RST_TABLES, rst_table_lines)


with open('C:/git_reps/google-cloud-python/bigquery/docs/snippets.py') as snippets:
    snip_code = snippets.read()

for del_code in code_deleted:
    snip_code = snip_code.replace(del_code, '')

snip_code = snip_code.split('\n')
snip_lines = []
for line in snip_code:
    if not '[END' in line:
        snip_lines.append(line)

new_snip_code = '\n'.join(snip_lines)

with open('C:/git_reps/google-cloud-python/bigquery/docs/snippets.py', 'w') as snippets:
    snippets.write(new_snip_code)
