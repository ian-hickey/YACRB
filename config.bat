@echo off
setlocal enabledelayedexpansion

echo Enter your GITHUB_API_KEY:
set /p GITHUB_API_KEY=

echo Enter your CHATGPT_API_KEY:
set /p CHATGPT_API_KEY=

echo Enter the REPO_OWNER (e.g., for 'https://github.com/{REPO_OWNER}/{REPO_NAME}'):
set /p REPO_OWNER=

echo Enter the REPO_NAME (e.g., for 'https://github.com/{REPO_OWNER}/{REPO_NAME}'):
set /p REPO_NAME=

echo Enter the MODEL (e.g., for paid gpt-4, otherwise try, gpt-3.5-turbo, or gpt-3.5-turbo-16k):
set /p MODEL=

(
echo {
echo     "GITHUB_API_KEY": "!GITHUB_API_KEY!",
echo     "CHATGPT_API_KEY": "!CHATGPT_API_KEY!",
echo     "REPO_OWNER": "!REPO_OWNER!",
echo     "REPO_NAME": "!REPO_NAME!",
echo     "MODEL": "!MODEL!"
echo }
) > config.json

endlocal
