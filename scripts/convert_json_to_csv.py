import csv
import sys
import json

# !!! does not always work
def convert_json_to_csv(json_data, output_csv):
    """
    Converts a list of JSON objects to a CSV file.
    Keeps column order based on the first JSON object, including ordered nested fields.
    Splits 'cleaned_text' into parts if it exceeds Excel's max cell character limit.
    """
    if not json_data:
        print("No data to write.")
        return

    max_cell_length = 32500  # Excel-safe limit

    # Determine number of parts needed for cleaned_text
    max_parts = 1
    for entry in json_data:
        text = entry.get("cleaned_text", "")
        parts = (len(text) - 1) // max_cell_length + 1 if text else 1
        max_parts = max(max_parts, parts)

    # Extract initial key order from first JSON object
    first_entry = json_data[0]
    fieldnames = []

    for key in first_entry:
        if key == "cleaned_text":
            # Insert cleaned_text and parts in order
            fieldnames.append("cleaned_text")
            if max_parts > 1:
                fieldnames.extend([f"cleaned_text_part{i}" for i in range(2, max_parts + 1)])
        elif key == "summary_data":
            # Add nested summary_data keys in their insertion order
            summary_data = first_entry["summary_data"]
            if isinstance(summary_data, dict):
                fieldnames.extend(summary_data.keys())
        else:
            fieldnames.append(key)

    try:
        with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for entry in json_data:
                row = {}

                for key in first_entry:
                    if key == "cleaned_text":
                        text = entry.get("cleaned_text", "")
                        chunks = [text[i:i + max_cell_length] for i in range(0, len(text), max_cell_length)]
                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                row["cleaned_text"] = chunk
                            else:
                                row[f"cleaned_text_part{i + 1}"] = chunk
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
    

if __name__ == "__main__":
    # open_csv("Telecoms_Grouped.csv")

    if len(sys.argv) < 2: # Error: No input file provided
        print("ERROR - Correct Usage: python analyse.py <input.json> <output.csv>")
        sys.exit(1)

    input_json = sys.argv[1] # Assumes correct file name
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)  # e.g. a list of JSON objects

    convert_json_to_csv(data, input_json[:-5] + ".csv")
