import json
import boto3
import sys
import configparser
import re

class AnalyseData:
    """A class to encapsulate the data analysis process."""

    def __init__(self, input_json=None, config_path=None):
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

    def _setup_config(self, config_path):
        """Setup configuration and parse command-line arguments."""
        # Config file setup
        self.config = configparser.ConfigParser()
        self.config.read(config_path) 
        
        # Read config for tokens and the AWS Bedrock prompt
        try:
            self.tokens = self.config.get("data", "tokens")
            self.prompt_template = self.config.get("prompt", "prompt_template")
        except Exception as e:
            print(f"Error: config.ini is missing required fields: {e}")
            sys.exit(1)

    def analyse_with_bedrock(self, prompt, model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0"):
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

    def run(self):
            """Run the main analysis pipeline."""
            
            with open(self.input_json, "r", encoding="utf-8") as f:
                data = json.load(f)  # e.g. a list of JSON objects
            prompt_template = self.prompt_template

            # Process each JSON object
            total = len(data)
            i = 1
            for obj in data:
                text_to_summarise = obj['cleaned_text']
                news_title = obj['title']
                print(f"({i}/{total}) Summarising: {news_title}" )
                i +=1

                prompt = prompt_template.format(title=news_title, cleaned_text=text_to_summarise)

                # Call AWS Bedrock summarization API with prompt
                response = self.analyse_with_bedrock(prompt)
                
                # Add summary back into the JSON object or store it separately
                obj["summary_data"] = response[0]

            output_name = self.input_json[:-5] + '_output.json'
            # Save updated data if needed
            with open(output_name, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=9)
            print("Analysis completed successfully!")

            return output_name

if __name__ == "__main__":
    """Main function to orchestrate the analysis process using the class."""
    if len(sys.argv) != 2: # Error: No input file provided
        print("ERROR - Correct Usage: python analyse.py <input.json>")
        sys.exit(1)

    input_json = sys.argv[1] # Assign input_json to the first argument
    ANALYSE_CONFIG_PATH = "examples/summary_example.ini"
    print("Starting analysis...")
    analyzer = AnalyseData(input_json, ANALYSE_CONFIG_PATH)
    analyzer.run()

