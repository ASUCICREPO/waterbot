from dotenv import load_dotenv
import os
import json
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

load_dotenv()  # take environment variables from .env.

# Set the directory where the JSON files are located
data_dir = 'raw_data'
__ds = TypeDeserializer()
__sr = TypeSerializer()


def deserialize_item(d: dict) -> dict:
    """Dynamo has crazy serialization and they don't always get rid of it for us."""
    return {k: __ds.deserialize(d[k]) for k in d}
def serialize_item(d: dict) -> dict:
    return {k: __sr.serialize(d[k]) for k in d}


for filename in os.listdir(data_dir):
    if filename.endswith('.json'):
        # Construct the full file path
        file_path = os.path.join(data_dir, filename)
        
        # Read the contents of the file
        with open(file_path, 'r') as f:
            # Split the file contents by newline to get each JSON payload
            for line in f:
                # Load the JSON payload into a Python dictionary
                payload = json.loads(line)
                data = deserialize_item(payload["NewImage"])
                print("=================================================================================")
                # Now you can work with the data
                print(json.dumps(data, indent=4))