import csv


def extract_csv(file_path):

    rows = []

    with open(
        file_path,
        newline="",
        encoding="utf-8",
        errors="ignore"
    ) as file:

        reader = csv.reader(file)

        for row in reader:

            rows.append(
                " ".join(row)
            )

    return "\n".join(rows)