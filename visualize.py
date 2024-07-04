import pandas as pd

# Replace 'your_file.csv' with the path to your CSV file
csv_file = 'properties.csv'

# Read the CSV file
df = pd.read_csv(csv_file)

# Display the CSV file content
print(df['address'])
