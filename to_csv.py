from operator import index
import pandas as pd
import re
import sys
from path import Path

def toRow(df, entry):
    row = {}
    row['job'] = entry['job']
    levels = ['L1', 'L2', 'L3', 'L4', 'L5']
    for i, node in enumerate(entry['nodes']):
        row[levels[i]] = ' '.join(df.loc[node].text.values)
    row['amount'] = df.loc[entry['nodes'][-1][-2]].text
    return row


def get_patern_of_bullet(String):
    regx = [
        ('\d{5}-\d+$', 70),
        ('[1-9][0-9]*(\.[1-9][0-9]*)*\)$', 20),
        ('\(\d*(\.?\d*)*\)$', 50),
        ('[1-9][0-9]*(\.[1-9][0-9]*)+$', 2),
        ('[1-9][0-9]*\.$', 1),
        ('[1-9][0-9]*$', 30)
    ]

    for r, l in regx:
        if re.match(r, String):
            if l in [2, 20, 50]:
                l = String.count('.') + l
            return r, l
    return '', 0


def main():
    src = Path(sys.argv[1])
    df = pd.read_csv(src)

    job = ''
    bulletFlag = False
    stack = []
    entries = []
    entry = []
    for filename in df.filename.unique():
        # print(filename)
        page = df[df['filename'] == filename][1:]
        lines = [[] for i in range(page.line_num.max()+1)]
        for i in page.index:
            lines[page.loc[i].line_num].append(i)
        for i in lines[::-1]:
            lineText = df.loc[i].text.values
            bullet = get_patern_of_bullet(df.loc[i[0]].text.split(' ')[0])

            if lineText[0].startswith('งาน:'):
                if (lineText[-1] == 'บาท'):
                    lineText = lineText[:-2]
                job = ' '.join(lineText)
            elif bullet[1]:
                bulletFlag = True

            if bulletFlag:
                entry += i
                if lineText[-1] == 'บาท':
                    # print(*df.loc[entry].text.values)
                    bulletFlag = False
                    entry_bullet = get_patern_of_bullet(
                        df.loc[entry[0]].text.split(' ')[0])
                    # print(entry_bullet[1], df.loc[entry[0]].text.split(' ')[0])
                    e = (entry, entry_bullet[1])
                    if len(stack) == 0:
                        stack.append(e)
                    elif e[1] > stack[-1][1]:
                        stack.append(e)
                    elif e[1] == stack[-1][1]:
                        entries.append(
                            {'job': job, 'nodes': [s[0].copy() for s in stack]})
                        stack.pop()
                        stack.append(e)
                    else:
                        entries.append(
                            {'job': job, 'nodes': [s[0].copy() for s in stack]})
                        while len(stack) > 0 and e[1] <= stack[-1][1]:
                            stack.pop()
                        stack.append(e)
                    entry = []

    entries.append({'job': job, 'nodes': [s[0].copy() for s in stack]})

    items = pd.DataFrame([toRow(df, e) for e in entries])
    dest_dir = Path('bud-csv')
    
    if not dest_dir.exists():
        dest_dir.mkdir()

    items.to_csv(f"{dest_dir}/{src.name[:src.name.rfind('.')]}_items.csv")

if __name__ == '__main__':
    main()