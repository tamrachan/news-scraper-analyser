import csv
import sys
import json

def convert_json_to_csv(json_data, output_csv, append_flag):
    """
    Converts a list of JSON objects to a CSV file.
    Keeps column order based on the first JSON object, including ordered nested fields.
    """
    if not json_data:
        print("No data to write.")
        return

    max_cell_length = 32500  # Excel-safe limit

    # Extract initial key order from first JSON object
    first_entry = json_data[0]
    fieldnames = []

    for key in first_entry:
        if key == "summary_data":
            # Add nested summary_data keys in their insertion order
            summary_data = first_entry["summary_data"]
            if isinstance(summary_data, dict):
                fieldnames.extend(summary_data.keys())
        else:
            fieldnames.append(key)

    if append_flag:
        open_type = "a"
    else:
        open_type = "w"

    try:
        with open(output_csv, open_type, newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for entry in json_data:
                row = {}

                for key in first_entry:
                    if key == "cleaned_text":
                        text = entry.get("cleaned_text", "")

                        if (len(text) > max_cell_length):
                            row["cleaned_text"] = text[:max_cell_length] + " [READ MORE FROM URL]"
                        else:
                            row["cleaned_text"] = text
                    elif key == "summary_data":
                        summary_data = entry.get("summary_data", {})
                        if isinstance(summary_data, dict):
                            for subkey in summary_data:
                                row[subkey] = summary_data.get(subkey, "")
                    else:
                        row[key] = entry.get(key, "")

                writer.writerow(row)

        print(f"Saved to {output_csv}")
    except Exception as e:
        print(e)

def open_csv(input_csv):
    """ Reads a csv file and prints it out """
    with open(input_csv, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            print(row)  # Each row is an OrderedDict (like a dict)
    
def main():
    # open_csv("Telecoms_Grouped.csv")

    if len(sys.argv) < 2: # Error: No input file provided
        print("ERROR - Correct Usage: python analyse.py <input.json> <output.csv>")
        sys.exit(1)

    input_json = sys.argv[1] # Assumes correct file name
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)  # e.g. a list of JSON objects

    convert_json_to_csv(data, input_json[:-5] + ".csv", False)

if __name__ == "__main__":
    main()