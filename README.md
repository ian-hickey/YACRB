# 🛠️ CodeReviewGPT 🤖
An automation tool that leverages OpenAI's GPT models to streamline code reviews on GitHub. With easy configuration options and a focus on efficiency, it's designed to enhance the code review process by providing AI-driven insights directly from GitHub diffs.

## 🔧 Configuration 

### 📁 Option 1: Using a Config File
Create a file named config.json in the same directory as the script.
Populate the file with the following structure:

`{
    "GITHUB_API_KEY": "YOUR_GITHUB_API_KEY",
    "CHATGPT_API_KEY": "YOUR_OPENAI_API_KEY",
    "REPO_OWNER": "GITHUB_REPO_OWNER",
    "REPO_NAME": "GITHUB_REPO_NAME"
`}

Replace the placeholders with the appropriate values.

Note: You can generate this config.json using the included config.sh script. 

Make sure the script is executable: 

`chmod +x config.sh`

Then you can run the script with `./config.sh` to generate the `config.json` file.


### 🌍 Option 2: Using Environment Variables
If you don't use a config.json file, the script will fallback to reading from environment variables. 

Ensure you have the following environment variables set:

* `export GITHUB_API_KEY="Your GitHub API key"`
* `export CHATGPT_API_KEY="Your OpenAI API key"`
* `export REPO_OWNER="The owner of the GitHub repository"`
* `export REPO_NAME="The name of the GitHub repository"`

## 🚀 Usage

Set up your configuration using one of the methods mentioned above.
Run the script using:

`python code-review.py`

The script will fetch pull requests and their diffs, and then use the OpenAI API to review the changes.

### 📊 Constants
* TOKEN_SIZE: This determines the maximum tokens to send at once when splitting diffs.
* MAX_TOKENS: This specifies the response size.
* MAX_DIFF_TOKEN_SIZE: This is the maximum token size of a diff past which the code review will be skipped.
  
### 📦 Dependencies

* requests
* json
* tiktoken
* time
* os

Ensure you have these libraries installed before running the script.
You can install them using:

`pip install requests json tiktoken`

Note: time and os are part of the Python standard library and don't need to be installed separately.
