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
@app.route("/ticker/<ticker>", methods=["GET"])
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

    background = get_company_background(ticker, filings)
    stats = get_company_stats(ticker, dp, filings)

    res = {"background": background, "stats": stats}

    return res, 200
    

# Gets the background info of a company via the corresponding 10-K segment
def get_company_background(ticker: str, filings: dict) -> str:
    # Get latest filing directory
    latest_filing_key = max(filings)
    latest_filing_folder = filings[latest_filing_key]
    filepath = f"sec-edgar-filings/{ticker}/10-K/{latest_filing_folder}/full-submission.txt"

    with open(filepath, "rb") as f:
        b = f.read()
        s = b.decode(encoding="utf-8")
        s = clean_data(s) # Filter HTML tags from data

        # Slice the text between the "Company Background" and "Markets and Distribution" sections
        start = find_nth_match(s, "Item 1.", 2) + len("Item 1.")
        end = start + 75000
        background_segment = s[start : end]
        with open("debug.txt", "w") as debug:
            debug.write(background_segment)
            debug.close()

        f.close()

    n = len("/full_submission.txt") + 21
    folder = filepath[:-n]
    output_filepath = f"{folder}/background.txt"

    if os.path.exists(output_filepath):
        with open(output_filepath, "r") as f:
            generated_background = f.read()
            f.close()
    else:
        # Generate background info from LLM
        generated_background = generate_content("Generate a brief markdown company summary from this", background_segment)

        with open(output_filepath, "w") as f:
            f.write(generated_background)
            f.close()

    return generated_background


def get_company_stats(ticker: str, dirpath: str, folders: dict) -> dict:
    folder = f"sec-edgar-filings/{ticker}/10-K"

    stats_dict = []
    
    for key, filing in folders.items():
        filename = f"{dirpath}/{filing}"
        filename = f"{filename}/full-submission.txt"

        with open(filename, "r", encoding="utf-8-sig") as f:
            s = f.read()
            s = clean_data(s) # Filter HTML tags from data

            f = open("debug.txt", "w")
            f.write(s)
            f.close()

            # Get n-th occurrence of "Item 8." and "Item 9."
            if s.count("Item 8.") == 1:
                n1 = 1
            else:
                n1 = 2

            if s.count("Item 9.") == 1:
                n2 = 1
            else:
                n2 = 2

            # Slice the text between "Item 8." and "Item 9."
            start = find_nth_match(s, "Item 8.", n1) + len("Item 8.")
            end = start + 200000

            stats_segment = s[start : end]

            f.close()
        
        # generated_pps = generate_content("What is the price per share for this stock. Answer as one simple number.", stats_segment)
        # generated_eps = generate_content("What is the price earnings share for this stock. Answer as one simple number.", stats_segment)
        generated_pps = 0
        generated_eps = 0

        year = int(key) - 5
        stats_dict.append({"year": year, "pps": generated_pps, "eps": generated_eps})
        print(stats_dict)
    
    return stats_dict
    

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
