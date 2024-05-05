import os
import re
from dotenv import load_dotenv
from flask import Flask, json, jsonify
from sec_edgar_downloader import Downloader
import google.generativeai as genai
import markdown

load_dotenv()

gemini = genai.GenerativeModel("gemini-pro")
app = Flask(__name__)

# Query by ticker
@app.route("/ticker/<ticker>", methods=["POST"])
def get_ticker_info(ticker: str):
    ticker = ticker.upper()
    # Download 10-K records
    if not os.path.exists(f"sec-edgar-filings/{ticker}"):
        # Set up downloader credentials
        email = os.getenv("SEC_EMAIL")
        dl = Downloader("Georgia Tech", email)

        # Download 10-K records from 1995 to 2023
        dl.get("10-K", ticker, after="1995-01-01", before="2024-01-01", download_details=True)

    folder = f"sec-edgar-filings/{ticker}/10-K"

    # Get filings with keys as indices beginning at 0 and values as corresponding folder
    # Add 5 to keys since 1995 takes 5 to get to 2000 --> 00
    (dp, dn, fn) = list(os.walk(folder))[0]
    filings = {(int(f[11:13]) + 5) % 100 : f for f in dn}
    filings = dict(sorted(filings.items())) # Sort filings by year

    # Get latest filing directory
    latest_filing_key = max(filings)
    latest_filing_folder = filings[latest_filing_key]
    filepath = f"sec-edgar-filings/{ticker}/10-K/{latest_filing_folder}/full-submission.txt"

    response = ""

    with open(filepath, "rb") as f:
        b = f.read()
        s = b.decode(encoding="utf-8")
        s = clean_data(s) # Filter HTML tags from data

        # Slice the text between the "Company Background" and "Markets and Distribution" sections
        start = find_nth_match(s, "Item 1.", 2) + len("Item 1.")
        end = start + 75000
        print(start, end)
        background = s[start : end]
        with open("debug.txt", "w") as debug:
            debug.write(background)
            debug.close()
    
        # Get company background from latest 10-K file
        response = get_company_background(filepath, background)

        f.close()

    res = {"background": response}

    return res, 200
    

# Gets the background info of a company via the corresponding 10-K segment
def get_company_background(filepath: str, background_segment: str):
    response = ""
    n = len("/full_submission.txt") + 21
    folder = filepath[:-n]
    output_filepath = f"{folder}/background.txt"

    if os.path.exists(output_filepath):
        with open(output_filepath, "r") as f:
            response = f.read()
            f.close()
    else:
        # Generate background info from LLM
        response = generate_content("Generate a brief markdown company summary from this", background_segment)

        with open(output_filepath, "w") as f:
            f.write(response)
            f.close()

    return response
    

def clean_data(s: str) -> str:
    html_filter = re.compile("<.*?>")
    utf_filter = re.compile("&.*?;|\r|\n")
    s = re.sub(html_filter, " ", s)
    s = re.sub(utf_filter, "", s)
    return s


# Generate LLM response based on prompt and portion of 10-K data
def generate_content(prompt: str, data: str):
    response = gemini.generate_content(f"{prompt}: {data}")

    print(response.text)
    
    formatted_response = format_response(response.text)

    return formatted_response

def format_response(response: str):
    # response = re.sub(r"([^\s\w,\.\-]|_)+", "", response)
    # response = re.sub(r"\*\*.*?\*\*", r"\<b\>.*?\</b\>", response)

    formatted_response = markdown.markdown(response)
    formatted_response = re.sub("\n", "", formatted_response)
    formatted_response = re.sub("\*", "", formatted_response)

    return formatted_response


def find_nth_match(s: str, match: str, n: int):
    s = s.upper()
    match = match.upper()

    count = 0
    index = 0
    while count < n:
        index = s.find(match, index)
        if index == -1:
            return -1
        count += 1
        index += len(match)
    return index


if __name__ == "__main__":
    app.run(port=8080)
