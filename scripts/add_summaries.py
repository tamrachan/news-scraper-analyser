import json
import boto3
import sys
import configparser
import re

ANALYSE_CONFIG_PATH = "../examples/summary_example.ini"

class AnalyseData:
    """A class to encapsulate the data analysis process."""

    def __init__(self, input_json: str=None, config_path: str=None):
        """Initialize the analysis object and setup the environment."""

        # Check that input_json has been provided
        if not input_json:
            print("ERROR: No input json was provided to analyse.")
            sys.exit(1)
        else:
            self.input_json = input_json
        # Check that config_path has been provided
        if not config_path:
            print("ERROR: No path to the config .ini file was provided.")
            sys.exit(1)

        # Get config file and set up
        self._setup_config(config_path)

    def _setup_config(self, config_path: str):
        """Setup configuration and parse command-line arguments."""
        # Config file setup
        self.config = configparser.ConfigParser()
        self.config.read(config_path) 
        
        # Read config for tokens and the AWS Bedrock prompt
        try:
            self.tokens = self.config.get("data", "tokens")
            self.analyse_prompt_template = self.config.get("analyse_prompt", "prompt_template")
            self.de_duplicate_prompt_template = self.config.get("de_duplicate_prompt", "prompt_template")
        except Exception as e:
            print(f"Error: config.ini is missing required fields: {e}")
            sys.exit(1)

    def parse_json_response(self, text: list):
        # Try to extract JSON from the response
        parsed = []
        
        # First, try to find JSON array pattern
        array_match = re.search(r'\[.*?\]', str(text), re.DOTALL)
        if array_match:
            try:
                array_text = array_match.group(0)
                parsed = json.loads(array_text)
                if isinstance(parsed, list):
                    return parsed
            except Exception as e:
                print(f"Error parsing JSON array: {e}")
        
        # If array parsing failed, try to find individual JSON objects
        # Look for complete JSON objects with proper structure
        json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', str(text), re.DOTALL)
        
        for obj_str in json_objects:
            try:
                # Clean up the JSON string
                cleaned_str = obj_str.strip()
                # Remove any trailing commas before closing braces
                cleaned_str = re.sub(r',\s*}', '}', cleaned_str)
                cleaned_str = re.sub(r',\s*]', ']', cleaned_str)
                
                parsed_obj = json.loads(cleaned_str)
                parsed.append(parsed_obj)
            except Exception as e:
                print(f"Error parsing JSON object: {e}")
                print(f"Problematic JSON string: {obj_str}")
                continue

        return parsed


    def analyse_with_bedrock(self, prompt: str, model_id: str="us.anthropic.claude-3-5-sonnet-20241022-v2:0") -> list:
        # Set up AWS Bedrock
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": int(self.tokens), # CHANGE IF MORE TOKENS NEEDED
            "temperature": 0.2
        }

        try:
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                accept="application/json",
                contentType="application/json"
            )
            result = json.loads(response['body'].read())
            content = result.get("content", "")
        except Exception as e:
            print(f"Error invoking Bedrock: {e}")
            sys.exit(1)

        # If content is a list with 'type':'text', extract the 'text' field
        if isinstance(content, list) and content and isinstance(content[0], dict) and 'text' in content[0]:
            text = content[0]['text']
        else:
            text = content

        print(text) # Print AWS Bedrock output

        return text
        

    def remove_duplicate_articles(self, json_list: list) -> list:
        prompt_template = self.de_duplicate_prompt_template
        summarised_data = []
        for i, obj in enumerate(json_list):
            summarised_data.append([i, obj["title"], obj["summary_data"]["summary"]])

        # print(summarised_data)
        prompt = prompt_template.format(data=summarised_data)

        # Get indexes of duplicates to remove
        response = self.analyse_with_bedrock(prompt)
        # print(response)
        response_converted = json.loads(response)

        # Extract all numbers
        indexes_to_remove = []
        for dct in response_converted:
            for sublist in dct.values():
                indexes_to_remove.extend(sublist)

        # Convert to list of ints and sort descending
        indexes_to_remove = [int(i) for i in indexes_to_remove]
        indexes_to_remove = sorted(set(indexes_to_remove), reverse=True)

        # Remove indexes in descending order so correct items are removed
        for index in indexes_to_remove:
            if 0 <= index < len(summarised_data):
                json_list.pop(index)

        return json_list

    def run(self) -> str:
        with open(self.input_json + ".json", "r", encoding="utf-8") as f:
            data = json.load(f)  # a list of JSON objects
        analyse_prompt_template = self.analyse_prompt_template

        # Process each JSON object
        total = len(data)
        for i, obj in enumerate(data):
            text_to_summarise = obj['cleaned_text']
            news_title = obj['title']
            print(f"({i}/{total}) Summarising: {news_title}" )

            analyse_prompt = analyse_prompt_template.format(title=news_title, cleaned_text=text_to_summarise)

            # Call AWS Bedrock summarization API with prompt
            response = self.analyse_with_bedrock(analyse_prompt)
            parsed_response = self.parse_json_response(response)
            
            # Add summary back into the JSON object or store it separately
            obj["summary_data"] = parsed_response[0]

        # Append data
        try:
            with open(self.input_json + "_output.json", "r", encoding="utf-8") as file:
                appended_data = data.extend(json.load(file))
        except FileNotFoundError:
            appended_data = data
            print("File not found. Writing to file instead of appending.")

        with open(self.input_json + '_output.json', "w", encoding="utf-8") as f:
            json.dump(appended_data, f, ensure_ascii=False, indent=9)
        
        print("--- Analysis completed successfully! Attempting to remove duplicates now... ---")

        # Remove duplicate summaries - only run on the articles added
        list_to_save = self.remove_duplicate_articles(data)

        # Append data
        try:
            with open(self.input_json + "_output.json", "r", encoding="utf-8") as file:
                list_to_save = list_to_save.extend(json.load(file))
        except FileNotFoundError:
            print("File not found. Writing to file instead of appending.")

        # Save updated data and appended data
        with open(self.input_json + '_output_AI.json', "w", encoding="utf-8") as f:
            json.dump(list_to_save, f, ensure_ascii=False, indent=9)
        print("Duplicates removed successfully!")

        return (self.input_json + '_output_AI.json')
            
# def test_de_duplicates(input_json: str):
#     #Lines 35 and 45
#     with open(input_json, "r", encoding="utf-8") as f:
#             data = json.load(f)  # e.g. a list of JSON objects
#     analyser = AnalyseData(input_json, ANALYSE_CONFIG_PATH)
#     analyser.remove_duplicate_articles(data)

def main():
    """Main function to orchestrate the analysis process using the class."""
    if len(sys.argv) != 2: # Error: No input file provided
        print("ERROR - Correct Usage: python analyse.py <input.json>")
        sys.exit(1)

    input_json = sys.argv[1] # Assign input_json to the first argument
    
    print("Starting analysis...")
    analyser = AnalyseData(input_json, ANALYSE_CONFIG_PATH)
    analyser.run()

if __name__ == "__main__":
    main()

