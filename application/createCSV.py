import csv
import os
from mappings.knowledge_sources import knowledge_sources


# Specify the filename
print("Current Working Directory:", os.getcwd())
csv_filename = 'D:\\Users\\anjana ouseph\\waterbot\\application\\KnowledgeSources.csv'

# Writing to csv file
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    # Writing the headers
    writer.writerow(['Name', 'URL', 'Description'])
    
    # Writing data rows
    for name, info in knowledge_sources.items():
        writer.writerow([name, info['url'], info.get('description', 'No description provided')])

print(f"CSV file created: {csv_filename}")
