#!/bin/bash

# Prompt user for GitHub API Key
read -p "Enter your GitHub API Key: " github_api_key

# Prompt user for OpenAI API Key
read -p "Enter your OpenAI API Key: " chatgpt_api_key

# Explain where to find the repo owner and repo name from a GitHub repo link
echo "From a GitHub repo link like 'https://github.com/OWNER/REPO_NAME',"
echo "'OWNER' is the repository owner and 'REPO_NAME' is the repository name."

# Prompt user for repo owner
read -p "Enter the repository owner (OWNER from the link): " repo_owner

# Prompt user for repo name
read -p "Enter the repository name (REPO_NAME from the link): " repo_name

# Generate the config.json file
cat <<EOL > config.json
{
    "GITHUB_API_KEY": "$github_api_key",
    "CHATGPT_API_KEY": "$chatgpt_api_key",
    "REPO_OWNER": "$repo_owner",
    "REPO_NAME": "$repo_name"
}
EOL

echo "config.json generated successfully!"
