
import os
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING
from neo4j import GraphDatabase

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-development-key")

# MongoDB connection
mongo_client = MongoClient(
    os.getenv("MONGODB_URI"),
    serverSelectionTimeoutMS=5000
)
db = mongo_client[os.getenv("MONGODB_DB", "movie_recommender")]

# Neo4j connection
neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(
        os.getenv("NEO4J_USERNAME", "neo4j"),
        os.getenv("NEO4J_PASSWORD")
    )
)

NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

@app.route("/")
def home():
    search = request.args.get("search", "").strip()
    genre = request.args.get("genre", "All")

    query = {}

    if search:
        query["title"] = {"$regex": search, "$options": "i"}

    if genre != "All":
        query["genres"] = genre

    movies = list(
        db.movies.find(query).sort("rating", DESCENDING)
    )

    all_genres = sorted({
        g
        for movie in db.movies.find({}, {"genres": 1})
        for g in movie.get("genres", [])
    })

    return render_template(
        "index.html",
        movies=movies,
        genres=all_genres,
        search=search,
        selected_genre=genre
    )

@app.route("/movie/<movie_id>", methods=["GET", "POST"])
def movie_details(movie_id):
    movie = db.movies.find_one({"movie_id": movie_id})

    if not movie:
        return "Movie not found", 404

    if request.method == "POST":
        reviewer = request.form.get("reviewer", "").strip()
        review_text = request.form.get("review", "").strip()

        try:
            rating = int(request.form.get("rating", "0"))
        except ValueError:
            rating = 0

        if not reviewer or not review_text:
            flash("Please enter your name and review.", "error")
        elif len(reviewer) > 50 or len(review_text) > 1000:
            flash("Your name or review is too long.", "error")
        elif rating < 1 or rating > 5:
            flash("Choose a rating between 1 and 5.", "error")
        else:
            db.reviews.insert_one({
                "movie_id": movie_id,
                "movie_title": movie["title"],
                "reviewer": reviewer,
                "rating": rating,
                "text": review_text,
                "created_at": datetime.now(timezone.utc)
            })

            flash("Your review has been saved!", "success")
            return redirect(url_for("movie_details", movie_id=movie_id))

    reviews = list(
        db.reviews.find({"movie_id": movie_id})
        .sort("created_at", DESCENDING)
    )

    return render_template(
        "movie.html",
        movie=movie,
        reviews=reviews
    )

@app.route("/recommend")
def recommend():
    movie_id = request.args.get("movie_id", "")

    movies = list(db.movies.find().sort("title", 1))
    selected = db.movies.find_one({"movie_id": movie_id})
    recommendations = []
    method = "Select a movie to begin."

    if selected:
        with neo4j_driver.session(
            database=NEO4J_DATABASE
        ) as session:
            result = session.run("""
                MATCH (selected:Movie {movie_id: $movie_id})
                      -[:SIMILAR_TO]-
                      (recommended:Movie)
                RETURN recommended.movie_id AS movie_id,
                       recommended.rating AS rating
                ORDER BY rating DESC
                LIMIT 6
            """, movie_id=movie_id)

            recommended_ids = [
                record["movie_id"] for record in result
            ]

            # If no direct links exist, find movies sharing genres.
            if not recommended_ids:
                result = session.run("""
                    MATCH (selected:Movie {movie_id: $movie_id})
                          -[:IN_GENRE]->(g:Genre)
                          <-[:IN_GENRE]-(recommended:Movie)
                    WHERE recommended.movie_id <> $movie_id
                    RETURN recommended.movie_id AS movie_id,
                           count(g) AS shared_genres
                    ORDER BY shared_genres DESC
                    LIMIT 6
                """, movie_id=movie_id)

                recommended_ids = [
                    record["movie_id"] for record in result
                ]
                method = "Shared-genre graph recommendations"
            else:
                method = "Movie similarity graph recommendations"

        # MongoDB supplies the full details for the recommended movies.
        if recommended_ids:
            movie_map = {
                movie["movie_id"]: movie
                for movie in db.movies.find({
                    "movie_id": {"$in": recommended_ids}
                })
            }

            recommendations = [
                movie_map[mid]
                for mid in recommended_ids
                if mid in movie_map
            ]

    return render_template(
        "recommendations.html",
        movies=movies,
        selected=selected,
        recommendations=recommendations,
        method=method
    )

@app.route("/analytics")
def analytics():
    total_movies = db.movies.count_documents({})
    total_reviews = db.reviews.count_documents({})

    genre_counts = {}
    for movie in db.movies.find({}, {"genres": 1}):
        for genre in movie.get("genres", []):
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    top_movies = list(
        db.movies.find().sort("rating", DESCENDING).limit(5)
    )

    return render_template(
        "analytics.html",
        total_movies=total_movies,
        total_reviews=total_reviews,
        genre_counts=genre_counts,
        top_movies=top_movies
    )

if __name__ == "__main__":
    # Debug mode is intended for local development only.
    app.run(debug=True)