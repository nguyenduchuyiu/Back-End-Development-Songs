from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify the service is running."""
    return jsonify(status='healthy'), 200

@app.route('/count', methods=['GET'])
def count():
    """Return the number of documents in the songs collection."""
    count = db.songs.count_documents({})
    return {"count": count}, 200

@app.route('/song', methods=['GET'])
def songs():
    """Return all songs in the songs collection."""
    try:
        # Fetch all documents from the songs collection
        songs_cursor = db.songs.find({})
        # Convert the cursor to a list of songs
        songs_list = list(songs_cursor)
        # Parse the list of songs to JSON format
        songs_json = parse_json(songs_list)
        # Return the list of songs with a 200 OK status
        return {"songs": songs_json}, 200
    except Exception as e:
        app.logger.error(f"Error fetching songs: {str(e)}")
        return {"error": "An error occurred while fetching songs"}, 500

@app.route('/song/<id>', methods=['GET'])
def get_song_by_id(id):
    """Return a song by its ID from the songs collection."""
    try:
        # Find a song by its ID
        song = db.songs.find_one({"id": int(id)})
        if song:
            # Parse the song to JSON format
            song_json = parse_json(song)
            # Return the song with a 200 OK status
            return song_json, 200
        else:
            # Return a 404 NOT FOUND if the song is not found
            return {"message": "song with id not found"}, 404
    except Exception as e:
        app.logger.error(f"Error fetching song by id: {str(e)}")
        return {"error": "An error occurred while fetching the song"}, 500

@app.route('/song', methods=['POST'])
def create_song():
    """Create a new song in the songs collection."""
    try:
        # Extract song data from the request body
        song_data = request.get_json()

        # Check if the song data contains an 'id'
        if 'id' not in song_data:
            return {"error": "Song data must include an 'id' field"}, 400

        # Check if a song with the given ID already exists
        existing_song = db.songs.find_one({"id": song_data['id']})
        if existing_song:
            # Return a 302 FOUND if the song with the ID already exists
            return {"Message": f"song with id {song_data['id']} already present"}, 302

        # Insert the new song into the collection
        db.songs.insert_one(song_data)

        # Return a success message with a 201 CREATED status
        return {"Message": "Song created successfully"}, 201
    except Exception as e:
        app.logger.error(f"Error creating song: {str(e)}")
        return {"error": "An error occurred while creating the song"}, 500

@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    """Update an existing song in the songs collection."""
    try:
        # Extract song data from the request body
        song_data = request.get_json()

        # Find the song by its ID
        existing_song = db.songs.find_one({"id": id})
        if not existing_song:
            # Return a 404 NOT FOUND if the song is not found
            return {"message": "song not found"}, 404

        # Check if the song data is the same as the existing song
        if existing_song == song_data:
            # Return a 200 OK with a specific message if nothing is updated
            return {"message": "song found, but nothing updated"}, 200

        # Update the song with the new data
        db.songs.update_one({"id": id}, {"$set": song_data})

        # Return a success message with a 200 OK status
        return {"message": "Song updated successfully"}, 200
    except Exception as e:
        app.logger.error(f"Error updating song: {str(e)}")
        return {"error": "An error occurred while updating the song"}, 500


@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    """Delete a song by its ID from the songs collection."""
    try:
        # Attempt to delete the song by its ID
        result = db.songs.delete_one({"id": id})
        
        # Check if a song was deleted
        if result.deleted_count == 0:
            # Return a 404 NOT FOUND if the song is not found
            return {"message": "song not found"}, 404
        
        # Return a 204 NO CONTENT if the song was successfully deleted
        return '', 204
    except Exception as e:
        app.logger.error(f"Error deleting song: {str(e)}")
        return {"error": "An error occurred while deleting the song"}, 500
######################################################################
