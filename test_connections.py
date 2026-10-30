"""Check connectivity to MongoDB and Neo4j."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase, TrustCustomCAs
from pymongo import MongoClient

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")


def check_mongodb() -> bool:
    """Ping MongoDB using MONGODB_URI (defaults to a local server)."""
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    try:
        with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
            client.admin.command("ping")
        print("MongoDB connection successful.")
        return True
    except Exception as exc:
        print(f"MongoDB connection failed: {exc}")
        return False


def check_neo4j() -> bool:
    """Verify Neo4j connectivity using NEO4J_* environment variables."""
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
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
        print(f"Neo4j connection failed: set {', '.join(missing)} in .env.")
        return False

    driver_config = {}
    trusted_ca = os.getenv("NEO4J_TRUSTED_CA")
    if trusted_ca:
        ca_path = Path(trusted_ca).expanduser()
        if not ca_path.is_absolute():
            ca_path = PROJECT_DIR / ca_path
        if not ca_path.is_file():
            print(f"Neo4j connection failed: CA certificate not found: {ca_path}")
            return False
        driver_config["trusted_certificates"] = TrustCustomCAs(str(ca_path))

    try:
        with GraphDatabase.driver(
            uri,
            auth=(username, password),
            **driver_config,
        ) as driver:
            driver.verify_connectivity()
        print("Neo4j connection successful.")
        return True
    except Exception as exc:
        print(f"Neo4j connection failed: {exc}")
        if "routing information" in str(exc).lower():
            print(
                "Check that the Aura instance is running, the URI is current, "
                "and outbound TCP port 7687 is allowed."
            )
        if any(
            message in str(exc).lower()
            for message in ("certificate_verify_failed", "self-signed certificate")
        ):
            print(
                "TLS certificate validation failed. If your network inspects TLS, "
                "ask its administrator for the trusted CA certificate and set "
                "NEO4J_TRUSTED_CA in .env to that certificate's path. "
                "Do not disable certificate verification."
            )
        return False


if __name__ == "__main__":
    results = (check_mongodb(), check_neo4j())
    sys.exit(0 if all(results) else 1)
