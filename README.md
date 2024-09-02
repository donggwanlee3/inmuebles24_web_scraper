# Inmuebles24 Web Scraper

This repository contains a web scraper built to collect data on real estate properties from the Inmuebles24 website (Mexico). The data is then processed and stored in the `/data` folder, and uploaded to an AWS S3 bucket.

## Features
- **Data Collection:** Scrapes all the properties data on the Inmuebles24 website, achieving approximately 95% data accuracy.
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

    You can get your ScraperAPI key [here](https://www.scraperapi.com/solutions/scraping-api/).

### Example Data

Example CSV data files are provided in the `example_csv_data` directory.

### Parent-Child Property Relationships

The scraper is designed to recognize and handle hierarchical relationships between properties:

- **Parent Properties:** Represent buildings that may contain multiple individual units or sub-buildings.
- **Child Properties:** Represent the individual units or sub-buildings within a parent property. The scraper captures details about each unit, including its relationship to the parent property.

This structure is particularly useful for real estate data where multiple listings may belong to the same building but have different attributes (e.g., floor plans, prices).

### Usage

#### Running Locally Without AWS Setup
When the web scraper is run, data will be stored in the `/data` folder and uploaded to AWS. If you want to run the scraper locally without setting up AWS, simply comment out line 173 in `web_scraper.py` and run the script:

```python
# Comment out this line in web_scraper.py if not using AWS:
# await upload_aws()
```

Then, to run the scraper, use:

```bash
python web_scraper.py
```

### File Structure

- **web_scraper.py** - The main script that runs the web scraping and data upload process.
- **aws.py** - Contains functions to upload CSV and GeoParquet files to S3.
- **requirements.txt** - Lists all the Python packages required to run the project.
- **example_csv_data/** - Directory containing example CSV data files for testing.
- **/data/** - Directory where scraped data will be stored locally.
- **.env** - Stores environment variables such as the ScraperAPI key and S3 bucket name.

### Contributions

Feel free to fork this repository, make your changes, and submit a pull request.
