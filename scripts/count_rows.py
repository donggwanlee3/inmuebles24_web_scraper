import csv
import sys

def count_rows_in_csv(file_path):
    try:
        with open(file_path, mode='r', newline='') as file:
            reader = csv.reader(file)
            row_count = sum(1 for row in reader)
        print(f"The number of rows in the CSV file is: {row_count}")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    csv_path = "csv_data/Building_Properties.csv"
    count_rows_in_csv(csv_path)
