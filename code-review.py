import requests
import json
import tiktoken
import time
import os
import re

GITHUB_API_URL = "https://api.github.com"
OPEN_AI_URL = "https://api.openai.com/v1/chat/completions"
HEADERS = {}
TOKEN_SIZE = 5120                    # Max tokens to send at once when splitting diffs
MAX_TOKENS = 2048                    # response size
MAX_DIFF_TOKEN_SIZE = 30000          # Max token size of a diff past which the code review is skipped
MODEL = "gpt-4"                      # This assumes you have api access to gpt-4 if not, change it to another model that you have access to (gpt-3.5-turbo)

def filter_diff(diff_text):
    """Filters the diff to remove minified css and js files, and ignore deletions."""
    # Split the diff text by sections
    sections = re.split(r'\ndiff --git', diff_text)
    
    # Add back the "diff --git" prefix removed during splitting (except for the first section)
    sections = [sections[0]] + ['diff --git' + section for section in sections[1:]]
    
    filtered_sections = []

    for section in sections:
        # Check if the section is for a minified or bundle file
        if re.search(r'\.(min\.js|min\.css)|bundle', section):
            continue
        
        # Check if the section is only for deleting/moving a file
        deletions = re.findall(r'^-', section, re.MULTILINE)
        additions = re.findall(r'^\+', section, re.MULTILINE)
        
        # If a file has been deleted (only deletions and the destination is /dev/null), skip it.
        if deletions and not additions and re.search(r'\+\+\+ /dev/null', section):
            continue
        
        # If a file has been renamed, skip it.
        if re.search(r'rename from', section) and re.search(r'rename to', section):
            continue
        
        filtered_sections.append(section)

    # Combine the filtered sections
    filtered_diff = '\n'.join(filtered_sections)
    return filtered_diff

# Load config from a JSON file or environment variables
def load_config():
    """Load configuration data from a JSON file named 'config.json'.
    If the file doesn't exist, fallback to environment variables."""
    CONFIG_FILE = "config.json"
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
    else:
         # Fallback to environment variables if config file is absent
        config['GITHUB_API_KEY'] = os.environ.get('GITHUB_API_KEY')
        config['CHATGPT_API_KEY'] = os.environ.get('CHATGPT_API_KEY')
        config['REPO_OWNER'] = os.environ.get('REPO_OWNER')
        config['REPO_NAME'] = os.environ.get('REPO_NAME')
    return config

# Load the configuration data
config = load_config()

# Extract individual config parameters
github_api_key = config['GITHUB_API_KEY']
chatgpt_api_key = config['CHATGPT_API_KEY']
repo_owner = config['REPO_OWNER']
repo_name = config['REPO_NAME']


def get_pull_request(owner, repo, pr_number):
    """Fetch a single pull request from a given GitHub repository.
    
    Parameters:
    - owner: The owner of the GitHub repository.
    - repo: The name of the GitHub repository.
    - pr_number: The pull request number.
    
    Returns:
    - A JSON response containing pull request details.
    """
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    response = requests.get(url, headers=HEADERS)
    return response.json()


def get_pull_request_diff(owner, repo, pr_number):
    """Fetch a single pull request from a given GitHub repository.
    
    Parameters:
    - owner: The owner of the GitHub repository.
    - repo: The name of the GitHub repository.
    - pr_number: The pull request number.
    
    Returns:
    - A text based DIFF response containing pull request changes.
    """
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}.diff"
    print(url)
    response = requests.get(url, headers=HEADERS)
    return filter_diff(response.text)

def count_tokens(token_list):
    return len(token_list)

def encode_segments(tokens, TOKEN_SIZE):
    """Chunk tokens into segments
    
    Parameters:
    - tokens: The tokens to chunk
    - TOKEN_SIZE: The number of tokens per chunk
    
    Returns:
    - A segment of size TOKEN_SIZE to send to CHATGPT
    """
    segments = []
    curr_len = 0
    curr_segment = []
    for token in tokens:
        curr_len += 1
        curr_segment.append(token)
        if curr_len >= TOKEN_SIZE: # example chunk size
            segments.append("".join(curr_segment))
            curr_segment = []
            curr_len = 0

    if curr_segment:
        segments.append("".join(curr_segment))
    
    return segments


def review_code_with_chatgpt(diff, chatgpt_api_key):
    """Get a code review from ChatGPT using the provided diff."""
    headers = {
        "Authorization": f"Bearer {chatgpt_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": """You are a code reviewer analyzing GitHub diffs. 
                Focus on style, best practices, and security. 
                Due to token limits, some diffs may be partial; do your best with available information. 
                Skip minified JavaScript, CSS, or other build byproducts. 
                If encountered, note: 'Skipping File.'
                """
            },
            {
                "role": "user",
                "content": f"{diff}"
            }
        ],
        "max_tokens": MAX_TOKENS
    }

    # Get token count 
    tokenizer = tiktoken.get_encoding("gpt2")
    tokens = tokenizer.encode(diff)
    
    # Chunk diff into segments under token limit
    token_strings = tokenizer.decode(tokens)

    # TODO: SKIP PR based on it being larger than the defined max. 
    segments = encode_segments(token_strings, TOKEN_SIZE)

    # Send segments and collect responses
    responses = []

    # TODO: Update this logic to try to keep more of the diff in the same conversation.
    totalTokenSent = 0
    for segment in segments:
        totalTokenSent += len(segment)
        print(f"Sending {len(segment)} tokens [{totalTokenSent} sent so far]\n")
        message = {
            "role": "user",
            "content": segment
        }

        data["messages"][1]= message
        
        response = requests.post(OPEN_AI_URL, headers=headers, data=json.dumps(data))  
        print(f"OpenAI Response Status Code: {response.status_code}\n")
        remaining_tokens = 10000 - totalTokenSent
        if response.status_code == 429 or remaining_tokens < TOKEN_SIZE:
            # Delay to avoid hitting rate limit
            if response.status_code == 429:
                print(f"Sleeping for 1 minute to avoid rate limiting [{response.status_code} Status code]\n")
                time.sleep(60)
                totalTokenSent = 0
            if remaining_tokens < TOKEN_SIZE:
                print(f"Sleeping for 20 seconds to avoid rate limiting [{remaining_tokens} tokens remaining]\n")
                time.sleep(20)

        if response.status_code not in [429, 200]:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            responses.append(response.json())
            print(get_full_review(responses)) # Dump the responses we have so far.
            print(f"Error from ChatGPT: {error_msg}\n")
            return f"Review failed due to an error: {error_msg}"
        
        responses.append(response.json())

    # Concatenate responses
    return get_full_review(responses)

def get_full_review(responses):
    full_review = ""
    for response in responses:
        if response is not None: 
            full_review += response.get('choices')[0].get('message', {}).get('content', '')

    return full_review

if __name__ == "__main__":
    pr_number = input("Enter the pull request number: ")

    HEADERS = {
        "Authorization": f"token {github_api_key}",
        "Accept": "application/vnd.github.v3+json"
    }

    pr = get_pull_request(repo_owner, repo_name, pr_number)
    print(f"Reviewing PR #{pr_number} - {pr['title']}")

    HEADERS = {
        "Authorization": f"token {github_api_key}",
        "Accept": "application/vnd.github.v3.diff"
    }
    diff = get_pull_request_diff(repo_owner, repo_name, pr_number)
    
    review = review_code_with_chatgpt(diff, chatgpt_api_key)

    # Print the review
    print("CODE REVIEW START" + ("-" * 75) + "\n")
    print(review)
    print("\nCODE REVIEW END" + ("-" * 77))


