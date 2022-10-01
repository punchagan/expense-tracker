# csvparser.py
import csv
import logging
log = logging.getLogger(__name__)

def parse_csv(filestream, select=None, types=None, has_headers=True, delimiter=',', silence_errors=False):
    '''
    Parse a delimiter separated file object into a list of records
    '''
    # if type(filestream) == str:
    #     print('The input should be a file object and not a string')
    #     print('Converting the filename string')
    #     filestream = open(filestream, 'rt')

    if select and not has_headers:
        raise RuntimeError("select argument requires column headers")

    rows = csv.reader(filestream, delimiter=delimiter)


    # Indices of the select columns
    indices = []
    # Check if the headers are present
    if has_headers:
        # Read the file headers
        headers = next(rows)
        # Select only desired columns
        if select:
            indices = [headers.index(select_ind) for select_ind in select]
            headers = select
    # Build the output for records
    records = []
    for row_ind, row in enumerate(rows, start=1):
        if not row:    # Skip rows with no data
            continue
        if indices:
            row = [row[index] for index in indices]
        if types:
            try:
                row = [func(val) for func, val in zip(types, row)]
            except ValueError as e:
                if not silence_errors:
                    log.warning("Row %d: Couldn't convert %s", row_ind, row)
                    log.debug("Row %d: Reason %s", row_ind, e)
                continue
        if has_headers:
            record = dict(zip(headers, row))
        else:
            record = tuple(row)
        records.append(record)

    return records
