import os
from dotenv import load_dotenv

load_dotenv(override=True)

uri = os.getenv("NEO4J_URI")

if uri:
    print("Neo4j URI loaded successfully.")
    print("URI scheme:", uri.split("://")[0] if "://" in uri else "Missing scheme")
    print("URI is empty:", not uri.strip())
else:
    print("ERROR: NEO4J_URI was not found.")