import csv
import datetime as dt
import logging

from constants import (BASE_DIR, DATETIME_FORMAT, NAME_FOLDER, OUTPUT_FILE,
                       OUTPUT_PRETTY)
from prettytable import PrettyTable

INFO_MESSAGE = 'Файл с результатами был сохранён: {file_path}'


def default_output(results, *cli_args):
    for row in results:
        print(*row)


def pretty_output(results, *cli_args):
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    results_dir = BASE_DIR / NAME_FOLDER
    results_dir.mkdir(exist_ok=True)
    parser_mode = cli_args.mode
    now_formatted = dt.datetime.now().strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = results_dir / file_name
    with open(file_path, 'w', encoding='utf-8') as csvfile:
        csv.writer(csvfile, csv.unix_dialect()).writerows(results)
    logging.info(INFO_MESSAGE.format(file_path=file_path))


CHOICES = {
    OUTPUT_PRETTY: pretty_output,
    OUTPUT_FILE: file_output,
    None: default_output
    }


def control_output(results, cli_args):
    CHOICES[cli_args.output](results, cli_args)
