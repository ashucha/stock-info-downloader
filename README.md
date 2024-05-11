# Insighter Trading

## Background

This is a tool that allows you to generate insights into stocks when you input their ticker. This is achieved via the Google Gemini API, which extracts this information from the company's 10-K filings from 1995 to 2023.

## Development

Insighter Trading was developed using a Flask API and a Google Gemini LLM on the back-end, with the front-end web app using Vanilla JS for dynamic rendering, Bootstrap for the design framework, and Chart JS to generate visualizations.

## Usage

The user opens the web app and inputs a ticker for which they would like to generate insights into an input form. This request is passed to the Flask API, which downloads 10-K filings for the ticker's company if it doesn't have them cached already. Then, it extracts valuable insights, such as company background (including name, industry, competitors, etc.) and financial metrics of the stock such as price per share (PPS) and earnings per share (EPS). PPS can be divided by EPS to get the price-to-earnings ratio (PE ratio), a metric commonly used by traders to understand whether or not a stock is undervalued. A PE ratio under 25 is generally considered an undervalued stock, meaning that it may be good to buy it. These are the insights that I chose to generate from the 10-K filings as they are useful to investors at any experience level and any size.
