import os
from dotenv import load_dotenv
from pymongo import MongoClient
from neo4j import GraphDatabase

load_dotenv()

mongo_client = MongoClient(os.getenv("MONGODB_URI"))
db = mongo_client[os.getenv("MONGODB_DB", "movie_recommender")]

neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(
        os.getenv("NEO4J_USERNAME", "neo4j"),
        os.getenv("NEO4J_PASSWORD")
    )
)

movies = [
    {
        "movie_id": "m1",
        "title": "Inception",
        "year": 2010,
        "genres": ["Sci-Fi", "Thriller"],
        "rating": 8.8,
        "description": "A thief enters people's dreams to steal secrets."
    },
    {
        "movie_id": "m2",
        "title": "Interstellar",
        "year": 2014,
        "genres": ["Sci-Fi", "Drama"],
        "rating": 8.7,
        "description": "Explorers travel through space to find humanity's future."
    },
    {
        "movie_id": "m3",
        "title": "The Dark Knight",
        "year": 2008,
        "genres": ["Action", "Crime", "Drama"],
        "rating": 9.0,
        "description": "Batman faces a dangerous criminal in Gotham."
    },
    {
        "movie_id": "m4",
        "title": "The Matrix",
        "year": 1999,
        "genres": ["Sci-Fi", "Action"],
        "rating": 8.7,
        "description": "A hacker discovers the truth about reality."
    },
    {
        "movie_id": "m5",
        "title": "Titanic",
        "year": 1997,
        "genres": ["Romance", "Drama"],
        "rating": 7.9,
        "description": "Two people fall in love aboard an ocean liner."
    },
    {
        "movie_id": "m6",
        "title": "Parasite",
        "year": 2019,
        "genres": ["Thriller", "Drama"],
        "rating": 8.5,
        "description": "A family becomes involved with a wealthy household."
    },
    {
        "movie_id": "m7",
        "title": "Avengers: Endgame",
        "year": 2019,
        "genres": ["Action", "Sci-Fi"],
        "rating": 8.4,
        "description": "Heroes reunite to save the universe."
    },
    {
        "movie_id": "m8",
        "title": "Get Out",
        "year": 2017,
        "genres": ["Horror", "Thriller"],
        "rating": 7.8,
        "description": "A weekend visit reveals unsettling secrets."
    }
]

# Store movie documents in MongoDB.
db.movies.create_index("movie_id", unique=True)
db.reviews.create_index("movie_id")

for movie in movies:
    db.movies.update_one(
        {"movie_id": movie["movie_id"]},
        {"$set": movie},
        upsert=True
    )

# Create graph nodes and relationships in Neo4j.
similar_pairs = [
    ("m1", "m2"),
    ("m1", "m4"),
    ("m3", "m7"),
    ("m4", "m7"),
    ("m6", "m8")
]

with neo4j_driver.session(
    database=os.getenv("NEO4J_DATABASE", "neo4j")
) as session:

    session.run("""
        CREATE CONSTRAINT movie_id_unique IF NOT EXISTS
        FOR (m:Movie) REQUIRE m.movie_id IS UNIQUE
    """)

    session.run("""
        CREATE CONSTRAINT genre_name_unique IF NOT EXISTS
        FOR (g:Genre) REQUIRE g.name IS UNIQUE
    """)

    for movie in movies:
        session.run("""
            MERGE (m:Movie {movie_id: $movie_id})
            SET m.title = $title,
                m.year = $year,
                m.rating = $rating
            WITH m
            UNWIND $genres AS genre_name
            MERGE (g:Genre {name: genre_name})
            MERGE (m)-[:IN_GENRE]->(g)
        """, movie_id=movie["movie_id"],
             title=movie["title"],
             year=movie["year"],
             rating=movie["rating"],
             genres=movie["genres"])

    for first_id, second_id in similar_pairs:
        session.run("""
            MATCH (a:Movie {movie_id: $first_id})
            MATCH (b:Movie {movie_id: $second_id})
            MERGE (a)-[:SIMILAR_TO]-(b)
        """, first_id=first_id, second_id=second_id)

neo4j_driver.close()
mongo_client.close()

print("Sample movies and graph relationships created successfully!")