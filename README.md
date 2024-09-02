# Inmuebles24 Web Scraper

This project contains a web scraper built to collect data on real estate properties from the Inmuebles24 website (Mexico). The data is then processed and uploaded to an AWS S3 bucket.

## Features
- **Data Collection:** Scrapes all the properties data on Inmuebles24website, achieving approximately 95% data accuracy.
- **Data Processing:** Converts CSV data into Parquet and GeoParquet formats for efficient storage and retrieval.
- **AWS Integration:** Uploads processed data to an Amazon S3 bucket.

## Setup

### Prerequisites
- Python
- `pip` package manager
- AWS credentials configured for `boto3` (if using AWS)

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/donggwanlee3/inmuebles24_web_scraper.git
    cd inmuebles24_web_scraper
    ```

2. Create and activate a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Create a `.env` file in the root directory of the project and add your ScraperAPI key and S3 bucket name:
    ```plaintext
    SCRAPERAPI='YOUR_API_KEY'
    BUCKET_NAME='your_bucket_name'
    ```

    You can get your ScraperAPI key [here]([https://www.scraperapi.com/](https://www.scraperapi.com/solutions/scraping-api/)).

### Example Data

Example CSV data files are provided in the `example_csv_data` directory. These files can be used to test the upload functions and ensure that the data is processed correctly.

### Parent-Child Property Relationships

The scraper is designed to recognize and handle hierarchical relationships between properties:

- **Parent Properties:** Represent buildings that may contain multiple individual units or sub-buildings.
- **Child Properties:** Represent the individual units or sub-buildings within a parent property. The scraper captures details about each unit, including its relationship to the parent property.

This structure is particularly useful for real estate data where multiple listings may belong to the same building but have different attributes (e.g., floor plans, prices).

### Usage

#### Running Locally Without AWS Setup
If you want to run the scraper locally without setting up AWS, simply comment out line 173 in `web_scraper.py` and run the script:

```python
# Comment out this line in web_scraper.py if not using AWS:
# await upload_aws()
When it's run, data will be stored in data folder.
