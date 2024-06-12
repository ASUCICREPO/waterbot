#!/bin/sh
. ./.env

# Rebuild raw_data directory
echo "REBUILDING RAW"
rm -rf raw_data
mkdir -p raw_data

# Synchronize S3 to Local
echo "SYNCING: $BUCKET"
aws s3 sync s3://$BUCKET .

# Loop through all the .json.gz files in the AWSDynamoDB/data/ directory
echo "EXTRACTING JSON PAYLOADS"
for file in AWSDynamoDB/data/*.json.gz
do
    # Extract the file to the raw_data directory
    gunzip -c "$file" > "raw_data/$(basename "$file" .json.gz).json"
done