# 🛠️ YACRB (Yet Another Code Review Bot) 🤖
An automation tool that leverages OpenAI's GPT models to streamline code reviews on GitHub. With easy configuration options and a focus on efficiency, it's designed to enhance the code review process by providing AI-driven insights directly from GitHub diffs. 
[Design Document](https://raw.github.com/ian-hickey/CodeReviewGPT/main/design.txt)

* Easy and fast setup - takes about a minute once you have keys
* Choose the pull request from a menu
* Doesn't require a node server
* Doesn't require giving unsecure access via Chrome Webstore
* Handles OpenAPI Rate Limiting

### 🖼️ Example Code Review
![Menu](https://raw.github.com/ian-hickey/yacrb/main/Screenshot-Menu.png?raw=true "Code Review")
![Code Review in terminal example](https://raw.github.com/ian-hickey/yacrb/main/example-edit-1.png?raw=true "Angular Code Review")

### 🔑 Generating API Tokens:

1. **GitHub API Token**:
To interact with private repositories or to avoid rate limits with public repositories, you'll need a GitHub API token. Here's how to generate one:

Visit your GitHub settings: https://github.com/settings/tokens.
Click on the "Generate new token" button.
Provide a note or description for your token (e.g., "CodeReviewGPT").
Under "Select Scopes", choose the necessary permissions for your token. For this script, "repo" access is usually sufficient for private repositories.
Click on the "Generate token" button at the bottom.
Copy the generated token and keep it safe. You won't be able to see it again!
Note: Always keep your tokens secret. Do not commit them or expose them in public places.

2. **OpenAI API Token**:
To get automated code reviews from ChatGPT, you'll need an OpenAI API token. Follow these steps:
Go to OpenAI's Platform website at platform.openai.com and sign in with an OpenAI account.
Click your profile icon at the top-right corner of the page and select "View API Keys."
Click "Create New Secret Key" to generate a new API key.

Copy the key for use in the config.json or as an environment variable.

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

**`Note: You can generate this config.json using the included config.sh script.`**

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

### 📦 Dependencies

* requests
* tiktoken
* tqdm
* termcolor

Ensure you have these libraries installed before running the script.
Install:

`pip install -r requirements.txt`

If you prefer you can install them manually:
`pip install {each library you need}`

## 🚀 Usage - Generate a code review!

Set up your configuration using one of the methods mentioned above.
Run the script using:

`python code-review.py`

The script will fetch pull requests and their diffs, and then use the OpenAI API to review the changes.

### 📊 Constants
* TOKEN_SIZE: This determines the maximum tokens to send at once when splitting diffs.
* MAX_TOKENS: This specifies the response size.
* MAX_DIFF_TOKEN_SIZE: This is the maximum token size of a diff past which the code review will be skipped.
  
