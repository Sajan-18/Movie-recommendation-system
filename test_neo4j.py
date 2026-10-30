import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "neo4j")

missing = [
    name
    for name, value in (
        ("NEO4J_URI", uri),
        ("NEO4J_USERNAME", username),
        ("NEO4J_PASSWORD", password),
    )
    if not value
]

if missing:
    raise RuntimeError(f"Missing Neo4j configuration: {', '.join(missing)}")

try:
    with GraphDatabase.driver(
        uri,
        auth=(username, password),
        connection_timeout=15,
    ) as driver:
        driver.verify_connectivity()
        print("Connection established successfully!")

        with driver.session(database=database) as session:
            result = session.run("RETURN 1 AS test")
            print("Test query result:", result.single()["test"])
except Exception as e:
    print("Error type:", type(e).__name__)
    print("Error details:", e)
    raise SystemExit(1) from e