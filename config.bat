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

(
echo {
echo     "GITHUB_API_KEY": "!GITHUB_API_KEY!",
echo     "CHATGPT_API_KEY": "!CHATGPT_API_KEY!",
echo     "REPO_OWNER": "!REPO_OWNER!",
echo     "REPO_NAME": "!REPO_NAME!"
echo }
) > config.json

endlocal
