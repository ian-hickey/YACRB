import sys
import requests
import json
import tiktoken
import os
import re
import argparse
from tqdm import tqdm
from termcolor import colored

from rate_limiter import RateLimiter

def print_asc_logo(): 
    logo = """
 .----------------.  .----------------.  .----------------.  .----------------.  .----------------. 
| .--------------. || .--------------. || .--------------. || .--------------. || .--------------. |
| |  ____  ____  | || |      __      | || |     ______   | || |  _______     | || |   ______     | |
| | |_  _||_  _| | || |     /  \     | || |   .' ___  |  | || | |_   __ \    | || |  |_   _ \    | |
| |   \ \  / /   | || |    / /\ \    | || |  / .'   \_|  | || |   | |__) |   | || |    | |_) |   | |
| |    \ \/ /    | || |   / ____ \   | || |  | |         | || |   |  __ /    | || |    |  __'.   | |
| |    _|  |_    | || | _/ /    \ \_ | || |  \ `.___.'\  | || |  _| |  \ \_  | || |   _| |__) |  | |
| |   |______|   | || ||____|  |____|| || |   `._____.'  | || | |____| |___| | || |  |_______/   | |
| |              | || |              | || |              | || |              | || |              | |
| '--------------' || '--------------' || '--------------' || '--------------' || '--------------' |
 '----------------'  '----------------'  '----------------'  '----------------'  '----------------' """
    git = """
⭐ Star us on Github: https://github.com/ian-hickey/YACRB
    """
    print(colored(logo, "yellow"))
    print(colored(git, "blue"))

GITHUB_API_URL = "https://api.github.com"
OPEN_AI_URL = "https://api.openai.com/v1/chat/completions"
HEADERS = {}
TOKEN_SIZE = 5120                   # Max tokens to send at once when splitting diffs
MAX_TOKENS = 2048                   # response size
MAX_DIFF_TOKEN_SIZE = 30000         # Max token size of a diff past which the code review is skipped
PER_PAGE = 10                       # How many pull requests to display per page in the menu
current_menu_page = 1               # When displaying the menu, the current page
next_url = None                     # The url for the next set of PR records

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
    If the file doesn't exist or some keys are missing, fallback to environment variables. 
    If some keys are still missing, prompt the user with detailed instructions and then save them to 'config.json'."""
    
    CONFIG_FILE = "config.json"
    config = {}
    
    # Attempt to load existing config file
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
    
    # Check each key and fallback to environment variables or prompt the user if they're missing
    prompts = {
        'GITHUB_API_KEY': "Enter your GitHub API Key: ",
        'CHATGPT_API_KEY': "Enter your OpenAI API Key: ",
        'REPO_OWNER': ("From a GitHub repo link like 'https://github.com/OWNER/REPO_NAME',\n"
                       "'OWNER' is the repository owner.\n"
                       "Enter the repository owner (OWNER from the link): "),
        'REPO_NAME': "Enter the repository name (REPO_NAME from the link): ",
        'MODEL': "Enter the model name (gpt-4 [paid], gpt-3.5-turbo, or gpt-3.5-turbo-16k): "
    }
    
    for key, prompt in prompts.items():
        if not config.get(key):
            config[key] = os.environ.get(key) or input(prompt)
    
    # Save updated config to file
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)
    
    return config

def load_prompts():
    """Load prompts data from a JSON file named 'prompts.json'."""
    CONFIG_FILE = "prompts.json"
    prompts = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            prompts = json.load(file)
    else:
        print(colored("Expected to find a file named prompts.json that contains the prompt selections. It is missing.", "red"))
        sys.exit()
    return prompts

def get_pull_requests(user, repo, next=""):
    params = {
        "per_page": PER_PAGE,
        "page": 1
    }
    HEADERS = {
        "Authorization": f"token {github_api_key}",
        "Accept": "application/vnd.github.v3+json"
    }

    if len(next):
        url = next
        params={}
    else: 
        url = f"https://api.github.com/repos/{user}/{repo}/pulls"

    response = requests.get(url, headers=HEADERS, params=params)
    global next_url
    next_url = get_next_link(response.headers.get("Link", ""))
    
    if response.status_code == 200:
        return response.json()
    else:
        print("Error:", response.status_code)
        return []

def get_pull_request(owner, repo, pr_number):
    """Fetch a single pull request from a given GitHub repository.
    
    Parameters:
    - owner: The owner of the GitHub repository.
    - repo: The name of the GitHub repository.
    - pr_number: The pull request number.
    
    Returns:
    - A JSON response containing pull request details.
    """
    HEADERS = {
        "Authorization": f"token {github_api_key}",
        "Accept": "application/vnd.github.v3+json"
    }
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
    HEADERS = {
        "Authorization": f"token {github_api_key}",
        "Accept": "application/vnd.github.v3.diff"
    }
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

def segment_diff_by_files(diff_text):
    """
    Segment the diff by individual files.
    
    Parameters:
    - diff_text: The entire diff text.
    
    Returns:
    - A list of segments, each segment corresponding to a file's diff.
    """
    
    # Split the diff text by sections
    sections = re.split(r'\ndiff --git', diff_text)
    
    # Add back the "diff --git" prefix removed during splitting (except for the first section)
    sections = [sections[0]] + ['diff --git' + section for section in sections[1:]]
    
    return sections

def review_code_with_chatgpt(diff, chatgpt_api_key, prompt_to_use, args):
    """
    Get a code review from ChatGPT using the provided diff.
    This version of the function segments the diff by files.
    """
    headers = {
        "Authorization": f"Bearer {chatgpt_api_key}",
        "Content-Type": "application/json"
    }
    
    # Get token count 
    tokenizer = tiktoken.get_encoding("gpt2")
    
    # Segment the diff by files
    file_segments = segment_diff_by_files(diff)
    
    # Store aggregated reviews
    aggregated_reviews = []
    rate_limiter = RateLimiter(3, 10000)
    segment_loader = tqdm(total=len(file_segments), position=0, leave=True, desc=colored(f'Reviewing Code', "white")) 
    for file_segment in file_segments:
        if not file_segment.strip():
            continue  # Skip empty segments

        tokens = tokenizer.encode(file_segment)
        token_strings = tokenizer.decode(tokens)

        # Chunk diff into segments under token limit
        segments = encode_segments(token_strings, TOKEN_SIZE)
        
        # Send segments and collect responses
        responses = []
        totalTokenSent = 0
        model_to_use = args.model if args.model is not None else model
        for segment in segments:
            totalTokenSent += len(segment)
            
            message = {
                "role": "user",
                "content": segment
            }
            
            data = {
                "model": model_to_use,
                "messages": [
                    {
                        "role": "system",
                        "content": prompt_to_use
                    },
                    message
                ],
                "max_tokens": MAX_TOKENS
            }

            response = rate_limiter.make_request(OPEN_AI_URL, method="POST", headers=headers, data=data)
            if response.status_code not in [429, 200]:
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                return f"Review failed due to an error: {error_msg}"
            responses.append(response.json())

        # Aggregate responses for the current file segment
        aggregated_reviews.append(get_full_review(responses))
        # Update the loader
        segment_loader.update(1)
    
    # Return the aggregated review
    segment_loader.close()
    return "\n\n".join(aggregated_reviews)

def get_full_review(responses):
    full_review = ""
    for response in responses:
        if response is not None: 
            full_review += response.get('choices')[0].get('message', {}).get('content', '')

    return full_review

def get_next_link(link_header):
    """
    Parse the Link header from GitHub API to get the next URL.
    """
    links = link_header.split(", ")
    
    for link in links:
        parts = link.split("; ")
        if len(parts) != 2:
            continue
        url, rel = parts
        if rel == 'rel="next"':
            # Remove < and > around the URL
            return url[1:-1]
    return None

def display_pr_menu(prs):
    global next_url
    print("\n")
    for idx, pr in enumerate(prs, 1):
        print(f"{idx}. {pr['title']} (#{pr['number']}) by {pr['user']['login']}")
    
    # If there are more than a page worth of menu options, display a more option.
    if next_url != None:
        print(colored(f"{len(prs) + 1}. More...", "light_blue"))

    choice_str = input(colored("\nEnter the number of the pull request you'd like to choose: ", "light_green"))
    choice = int(choice_str)
    if 1 <= choice <= len(prs)+1: # have to +1 to allow for more option
        # handle more option
        if len(prs)+1 == choice:
            if (next_url != None):
                return display_pr_menu(get_pull_requests(repo_owner, repo_name, next_url ))
        
        # handle regular selection
        selected_pr_number = prs[choice - 1]['number']
        return int(selected_pr_number)
    else:
        return None

def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate code reviews using ChatGPT.')
    parser.add_argument('-format', dest='format', choices=['plain', 'json', 'html'], default='plain',
                        help='Output format for the code review. Choices are plain, json, or html.')
    parser.add_argument('-output', dest='output_file', default=None,
                        help='Filename to save the code review. If not provided, the review is printed to the console.')
    # Read the keys from the prompts object
    keys_list = list(prompts.keys())
    parser.add_argument('-type', dest='review_type', choices=keys_list, default="general",
                        help=f'The type of code review to do. These will change if it reviews for security, performance etc.')
    parser.add_argument('-model', dest='model', choices=['gpt-4', 'gpt-3.5-turbo', 'gpt-3.5-turbo-16k'], default=None,
                        help='Change the model for this review')
    return parser.parse_args()

def format_review(review, format_type):
    if format_type == 'plain':
        return review
    elif format_type == 'json':
        return json.dumps({"review": review})
    elif format_type == 'html':
        with open("review_template.html", 'r') as template_file:
            html_template = template_file.read()
        
        # Split the review content by file sections
        file_sections = re.split(r'File: ', review)[1:]
        
        file_html_sections = []
        for section in file_sections:
            file_name, content = section.split('\n', 1)
            file_html = f'<h2>File: {file_name}</h2><p>{content}</p>'
            file_html_sections.append(file_html)
        
        # Replace the placeholder in the template with the populated file sections
        populated_html = html_template.replace('<!-- The following section will be repeated for each file in the review -->', '\n'.join(file_html_sections))
        
        return populated_html
 
if __name__ == "__main__":
    try:
        # Load the configuration data
        config = load_config()

        # Load the prompt data
        prompts = load_prompts()

        # Set the default prompt
        prompt = prompts['general']

        # Extract individual config parameters
        try: 
            github_api_key = config['GITHUB_API_KEY']
            chatgpt_api_key = config['CHATGPT_API_KEY']
            repo_owner = config['REPO_OWNER']
            repo_name = config['REPO_NAME']
            model = config['MODEL']
        except Exception as e:
            print(colored("An unexpected error occurred. Please ensure you have the config.json (OR ENV variables) and that they contain, keys, repo information, and model. Not found: ",'red'), e)
            exit()
        args = parse_arguments()
        print("\n")
        print_asc_logo()

        repo_own = input(colored(f"Enter a repo owner or enter to use the default [{repo_owner}]: ", "white"))
        if (len(repo_own) > 0): 
            repo_owner = repo_own

        repo = input(colored(f"Enter a repo name or enter to use the default [{repo_name}]: ", "white"))
        if (len(repo) > 0): 
            repo_name = repo
        # Display a menu of OPEN pull requests to the user. They display 10 at a time by default.
        # If there are no open pull requests, give the user an option to select a single closed/merged PR by number.
        prs = get_pull_requests(repo_owner, repo_name)
        if (len(prs) == 0):
            print(colored(f"\n\n*** There are no OPEN pull requests for {repo_name}. ***\n\n", "yellow"))
            pr_number = input(colored(f"To review a merged or closed PR, enter a PR number (https://www.github.com/{repo_owner}/{repo_name}/pulls/[pr_number]): ", "white"))
            pr = get_pull_request(repo_owner, repo_name, pr_number)
        else: 
            pr_number = display_pr_menu(prs) 
            pr = get_pull_request(repo_owner, repo_name, pr_number)
        
        print(f"Reviewing PR #{pr_number} - {pr['title']}")
        
        diff = get_pull_request_diff(repo_owner, repo_name, pr_number)

        if args.review_type:
            review = review_code_with_chatgpt(diff, chatgpt_api_key, prompts[args.review_type], args)
        else: 
            review = review_code_with_chatgpt(diff, chatgpt_api_key, prompt, args)
        formatted_review = format_review(review, args.format)
        

        if args.output_file:
            # Check if 'out' directory exists, if not, create it
            if not os.path.exists('out'):
                os.makedirs('out')

            # Ensure the output is saved in the 'out' subdirectory
            output_path = os.path.join('out', args.output_file)
            with open(output_path, 'w') as file:
                file.write(formatted_review)
                print("\n")
        else:
            print("\n")
            print(formatted_review)
            print("\n")
    except KeyboardInterrupt:
        print("\n" * 2)

