from flask import Flask, jsonify, render_template_string, request, render_template
from sentence_transformers import SentenceTransformer
import psycopg2
import json
import requests
from loguru import logger
from json2html import *

app = Flask(__name__)
qdrant_url = "http://qdrant:6333/"
qdrant_collection = "ttt_collection"


def get_db_connection():
    conn = psycopg2.connect(
        host="db",
        database="testdb",
        user="testuser",
        password="testpassword")
    return conn


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/test')
def test():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result[0] == 1:
        return jsonify({"message": "Connection successful"}), 200
    else:
        return jsonify({"message": "Connection failed"}), 500


@app.route('/initialize', methods=['GET'])
def initialize():
    conn = get_db_connection()
    cur = conn.cursor()

    # Truncate table
    cur.execute("TRUNCATE TABLE names")
    conn.commit()

    # Load names.json
    with open('names.json', 'r') as f:
        data = json.load(f)

    # Insert names into the names table
    for name in data['names']:
        first_name = name['firstName']
        last_name = name['lastName']
        combined_name = f"{first_name} {last_name}"
        cur.execute("INSERT INTO names (first_name, last_name, combined_name) VALUES (%s, %s, %s)",
                    (first_name, last_name, combined_name))
        conn.commit()

    cur.close()
    conn.close()

    return jsonify({"message": "Initialization completed successfully"}), 200


@app.route('/create', methods=['GET'])
def create():
    conn = get_db_connection()
    cur = conn.cursor()

    # Drop the names table if it exists
    cur.execute("DROP TABLE IF EXISTS names")
    conn.commit()

    # Create the names table
    cur.execute("""
        CREATE TABLE public.names
        (
            id            SERIAL,
            first_name    VARCHAR(500),
            last_name     VARCHAR(500),
            combined_name VARCHAR(1000)
        );
    """)
    conn.commit()

    # Alter the owner of the names table
    cur.execute("ALTER TABLE public.names OWNER TO testuser")
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"message": "Table creation completed successfully"}), 200


@app.route('/extensions', methods=['GET'])
def extensions():
    conn = get_db_connection()
    cur = conn.cursor()

    # Turn on extensions
    cur.execute("CREATE EXTENSION pg_trgm;")
    conn.commit()

    cur.execute("CREATE EXTENSION fuzzystrmatch;")
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"message": "Extensions turned on"}), 200


@app.route('/search/', methods=['GET'])
def search():
    return render_template("search.html")


@app.route('/initQdrant', methods=['GET'])
def init_qdrant():
    url = f"{qdrant_url}collections/{qdrant_collection}"
    headers = {"Content-Type": "application/json"}
    data = {"vector_size": 768, "distance": "Cosine"}

    response = requests.put(url, headers=headers, data=json.dumps(data))
    logger.info(response.text)

    return jsonify(str(response)), 200


@app.route('/upsert', methods=['GET'])
def upsert():
    model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
    url = f"{qdrant_url}collections/{qdrant_collection}/points"
    headers = {"Content-Type": "application/json"}
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
            SELECT id, combined_name
            FROM names;
        """)
    result = cur.fetchall()

    for name in result:
        embeddings = model.encode([name[1]])
        logger.info(name[1])

        data = {
            "batch": {
                "ids": [name[0]],
                "payloads": [
                    {"name": name[1]}
                ],
                "vectors": [
                    embeddings[0].tolist()
                ]
            }
        }

        requests.put(url, headers=headers, data=json.dumps(data))

    return jsonify(str(result)), 200


@app.route('/search/', methods=['POST'])
def search_post():
    if not request.form['search_term']:
        return jsonify({"message": "Search term is required"}), 400
    if not request.form['search_method']:
        return jsonify({"message": "Search method is required"}), 400
    if request.form['search_method'] not in ['SIMILARITY', 'SOUNDEX', 'LEVENSHTEIN', 'QDRANT', 'ALL']:
        return jsonify({"message": "Invalid search method"}), 400

    if request.form['search_method'] == 'SIMILARITY':
        result = similarity_search(request.form['search_term'])
    elif request.form['search_method'] == 'SOUNDEX':
        result = soundex_search(request.form['search_term'])
    elif request.form['search_method'] == 'LEVENSHTEIN':
        result = levenshtein_search(request.form['search_term'])
    elif request.form['search_method'] == 'QDRANT':
        result = qdrant_search(request.form['search_term'])
    elif request.form['search_method'] == 'ALL':
        result_similarity = similarity_search(request.form['search_term'])
        result_soundex = soundex_search(request.form['search_term'])
        result_lev = levenshtein_search(request.form['search_term'])
        result_qdrant = qdrant_search(request.form['search_term'])
        html_similarity = json2html.convert(json=result_similarity)
        html_soundex = json2html.convert(json=result_soundex)
        html_lev = json2html.convert(json=result_lev)
        html_qdrant = json2html.convert(json=result_qdrant)
        return render_template('data-template-all.html', data_similarity=html_similarity, data_soundex=html_soundex,
                               data_lev=html_lev, data_qdrant=html_qdrant)

    html_data = json2html.convert(json=result)
    return render_template('data-template.html', data=html_data)


def similarity_search(search_term):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT combined_name, SIMILARITY(combined_name, %s) AS similarity
        FROM names
        WHERE combined_name %% %s
        ORDER BY similarity DESC
        LIMIT 15;
    """, (search_term, search_term))
    result = cur.fetchall()

    cur.close()
    conn.close()

    return result


def soundex_search(search_term):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            combined_name, SIMILARITY(
            METAPHONE(combined_name,10),
            METAPHONE(%s,10)
            ) AS similarity
        FROM names
        ORDER BY SIMILARITY(
            METAPHONE(combined_name,10),
            METAPHONE(%s,10)
            ) DESC
        LIMIT 15;
    """, (search_term, search_term))
    result = cur.fetchall()

    cur.close()
    conn.close()

    return result


def levenshtein_search(search_term):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT combined_name, LEVENSHTEIN(combined_name, %s) AS distance
        FROM names
        WHERE combined_name %% %s
        ORDER BY distance ASC
        LIMIT 15;
    """, (search_term, search_term))
    result = cur.fetchall()

    cur.close()
    conn.close()

    return result


def qdrant_search(search_term):
    sentences = [search_term]

    model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
    embeddings = model.encode(sentences)
    url = f"{qdrant_url}collections/{qdrant_collection}/points/search"
    headers = {"Content-Type": "application/json"}
    data = {
        "params": {
            "hnsw_ef": 128,
            "exact": False
        },
        "vector": embeddings[0].tolist(),
        "limit": 15,
        "with_payload": True
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    results = response.json()["result"]
    iterator = map(lambda x: {"name": x["payload"]["name"], "score": x["score"]}, results)

    return list(iterator)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
