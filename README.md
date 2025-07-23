# news-scraper-analyser
This tool web scrapes specified news sites using Beautiful Soup and summarises/analyses each news article using AWS Bedrock AI.  

## How it works
There are two parts:
1. Collecting the data (`collect_data.py`)
2. Analysing the data (`add_summaries.py`)
To collect and analyse the data, use `main.py`.

## How to run
Below are instructions on how to use run the news scraper analyser.

### 1. Ensure Python is installed on your account.
You can check this by running the command `python --version` or `python3 --version` in your terminal.  
If "Python 3.11.9" or similar shows up, you have Python installed.  
If Python is not installed, you can download it from [The Official Website](https://www.python.org/downloads/) or from Microsoft Store (search "Python" and install the latest version).  

### 2. Clone the repository
Open the Command Prompt in the folder where you want the script.
Run the following command:
`git clone https://github.com/tamrachan/news-scraper-analyser.git`

### 3. Create a Virtual Environment
This will allow you to run the Python script without having to install the dependencies on your machine.    

Ensure you are in the correct file directory (i.e. in the "news-scraper-analyser" folder).  
You can do this by navigating to this folder in File Explorer, right-clicking on empty space within the folder and clicking "Open in Terminal".    

If it is your first time running the script, refer to Section 3.1, otherwise, refer to Section 3.2.

#### 3.1 First time running the script
If it is your first time running the script, you need to create the virtual environment.
Run the following commands, one at a time:
```powershell
python -m venv venv
./venv/Scripts/activate
```
There should be a (venv) to the left of the terminal like below.  
BEFORE:
```powershell
PS C:...\news-scraper-analyser>
```
AFTER:
```powershell
(venv) PS C:...\news-scraper-analyser>
```  
Then install the requirements:
```powershell
pip install -r requirements.txt
```

#### 3.2 Not your first time
If you have run the script before, you already have a virtual environment created with the dependencies.  
So the only command you need to run is:
```powershell
./venv/Scripts/activate
```  
This will activate your virtual environment previously created.

### 4. Specify websites to be scraped in a collect.ini file
Look at `collect_example.ini` as a template to see how your config file should be written. Specify which websites you want to web scrape here with the HTML elements detailed so Beautiful Soup can successfully scrape the news article.

### 5. Create a prompt in a summary.ini file
Look at `summary_example.ini` as a template to see how your prompt should be written.
If you do not write your prompt in this format, the python script will not recognise your instructions.

### 6. AWS environmental credentials
Paste your powershell AWS environmental credentials in your terminal to ensure AWS Bedrock can run. If you do not have an AWS account with Bedrock access, you cannot use this script.

### 7. Run the Python Script
To run the web scraper and analyser, run the following command:
```powershell
python main.py
```  
