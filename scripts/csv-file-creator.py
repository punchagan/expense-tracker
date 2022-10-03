# Standard libs
import csv
from pathlib import Path

# 3rd party libs
from bs4 import BeautifulSoup

# Local libs
import csvparser


def create_temp_csv(filepath, created_filepath, catch_word="Transaction Date", cc=True):
    """
    Performs cleaning of data of expenses csv file and returns the
    created_filepath.

    Takes filepath of the uncleaned csv, filepath to save the cleaned csv
    catch_word to start cleaning from and if it has cc in filename.

    """
    with open(filepath, "r") as inp, open(created_filepath, "w") as out:
        writer = csv.writer(out)
        start_mark = False
        end_mark = False
        for row in csv.reader(inp):
            try:
                if cc:
                    if catch_word in row[1]:
                        start_mark = True
                else:
                    if catch_word in row[0]:
                        start_mark = True
            except Exception as e:
                pass
            # Check if row is empty and then stop the iteration
            if row == []:
                if start_mark:
                    end_mark = True
                else:
                    continue
            if end_mark:
                break
            if start_mark:
                if cc:
                    writer.writerow(row[1:])
                else:
                    writer.writerow(row)
    return created_filepath


def create_csv_from_html(htmlfile, csv_output_file):
    """
    Converts expenses html file to a csv that can be cleaned.
    """
    soup = BeautifulSoup(open(htmlfile), "html.parser")
    table = soup.findAll("table")[1]
    rows = table.findAll("tr")
    # Create a csv file that can be passed to create_temp_csv
    with open(csv_output_file, "w") as html_csv_output:
        writer = csv.writer(html_csv_output)
        for row in rows:
            csv_row = []
            for cell in row.findAll(["td", "th"]):
                csv_row.append(cell.get_text())
            writer.writerow(csv_row[1:])
    return csv_output_file


if __name__ == "__main__":
    # Gather all records for each format - for further analysis
    HERE = Path(__file__).parent

    filename_1 = create_temp_csv(
        HERE.joinpath("../sample/axis-cc-statement.csv"), "axis-cc-temp.csv"
    )
    with open(filename_1, "r") as cleaned_csv1:
        records_cc_statement = csvparser.parse_csv(cleaned_csv1)

    filename_2 = create_temp_csv(
        HERE.joinpath("../sample/axis-statement.csv"),
        "axis-temp.csv",
        catch_word="Tran Date",
        cc=False,
    )
    with open(filename_2, "r") as cleaned_csv2:
        records_statement = csvparser.parse_csv(cleaned_csv2)

    filename_3 = create_temp_csv(
        create_csv_from_html(
            HERE.joinpath("../sample/axis-cc-statement.html"), "axis-temp-html.csv"
        ),
        "axis-cc-html.csv",
    )
    with open(filename_3, "r") as cleaned_html:
        records_html = csvparser.parse_csv(cleaned_html)
