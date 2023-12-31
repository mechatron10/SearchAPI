from flask import Flask, request, jsonify
import requests
from flask_caching import Cache
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
# Configure CORS to allow requests from your local frontend during development
CORS(app, resources={r"/search": {"origins": "https://frontend-search-api.vercel.app"}})
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
base_url = "https://app.ylytic.com/ylytic/test"

# Fetch and cache comments_data only once when the application starts
response = requests.get(base_url)
if response.status_code == 200:
    data = response.json()
    comments_data = data.get("comments", [])
    # Cache the comments_data for 1 hour (you can adjust the timeout as needed)
    cache.set('comments_data', comments_data, timeout=3600)
else:
    error_message = "Failed to fetch data from the API."
    print(error_message)

@app.route("/search", methods=["GET"])
def get_comments():
    # Check if comments_data is in the cache
    comments_data = cache.get('comments_data')
    if comments_data is None:
        # If not in the cache, fetch it from the external API and cache it
        response = requests.get(base_url)

        if response.status_code == 200:
            data = response.json()
            comments_data = data.get("comments", [])
            cache.set('comments_data', comments_data, timeout=3600)
        else:
            print("Failed to fetch data from the API.")
            comments_data = []

    # Get query parameters for filtering
    search_author = request.args.get("search_author")
    at_from = request.args.get("at_from")
    at_to = request.args.get("at_to")
    like_from = request.args.get("like_from")
    like_to = request.args.get("like_to")
    reply_from = request.args.get("reply_from")
    reply_to = request.args.get("reply_to")
    search_text = request.args.get("search_text")

    # Filter comments based on the specified criteria
    filtered_comments = []

    for comment in comments_data:
        if isinstance(comment, dict):
            author = comment.get("author", "").lower()
            at = str(comment.get("at", ""))
            like = comment.get("like", 0)
            reply = comment.get("reply", 0)
            text = comment.get("text", "").lower()
            try:
                at_datetime = datetime.strptime(at, "%a, %d %b %Y %H:%M:%S %Z")
            except ValueError:
                at_datetime = None  # Handle invalid 'at' values as None

            # Perform comparisons using strings
            # Split both search_text and text into words
            search_words = search_text.lower().split() if search_text else []
            comment_words = text.lower().split()

            # Check if search_words appear in the same sequence in comment_words
            if (
                (search_author is None or (search_author.strip() and search_author.lower() in author)) and
                (at_from is None or datetime.strptime(at, "%a, %d %b %Y %H:%M:%S %Z") >= datetime.strptime(at_from, "%a, %d %b %Y %H:%M:%S %Z")) and
                (at_to is None or datetime.strptime(at, "%a, %d %b %Y %H:%M:%S %Z") <= datetime.strptime(at_to, "%a, %d %b %Y %H:%M:%S %Z")) and
                (like_from is None or like >= int(like_from)) and
                (like_to is None or like <= int(like_to)) and
                (reply_from is None or reply >= int(reply_from)) and
                (reply_to is None or reply <= int(reply_to)) and
                all(word in comment_words for word in search_words) and  # Check if all words in search_text are present in text
                ' '.join(search_words) in ' '.join(comment_words)  # Check if search_words appear in comment_words
            ):
                filtered_comments.append(comment)

    return jsonify(filtered_comments)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
