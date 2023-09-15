# This module contains general functions

import requests
import re

def separate_symbol_and_trade_against(symbol):
    if symbol.endswith("BTC"):
        symbol_only = symbol[:-3]
        symbol_stable = symbol[-3:]
    elif symbol.endswith(("BUSD","USDT")):    
        symbol_only = symbol[:-4]
        symbol_stable = symbol[-4:]

    return symbol_only, symbol_stable

def extract_date_from_github_changelog():
    github_url = "https://github.com/jptsantossilva/BEC/raw/main/CHANGELOG.md"

    response = requests.get(github_url)
    if response.status_code == 200:
        content = response.text
        match = re.search(r'##\s*\[(.*?)\]', content)
        if match:
            return match.group(1)
        else:
            return None
    else:
        print("Failed to fetch the GitHub CHANGELOG.md content.")
        return None
    
def extract_date_from_local_changelog():
    file_path = "CHANGELOG.md"
    with open(file_path, 'r') as file:
        content = file.read()
        match = re.search(r'##\s*\[(.*?)\]', content)
        if match:
            return match.group(1)
        else:
            return None