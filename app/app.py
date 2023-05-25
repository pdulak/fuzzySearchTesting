from flask import Flask, jsonify, render_template_string, request
import psycopg2
import json

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host="db",
        database="testdb",
        user="testuser",
        password="testpassword")
    return conn


@app.route('/')
def home():
    html = """
    <p>Use the following links to interact with the database:</p>
    <ul>
        <li><a href="/test">Test DB connection</a></li>
        <li><a href="/create">Create the 'names' table</a></li>
        <li><a href="/initialize">Initialize the 'names' table</a></li>
        <li><a href="/extensions">Turn on extensions</a></li>
        <li><a href="/search">Test search</a></li>
    </ul>
    """
    return render_template_string(html)


@app.route('/test')
def test():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    result = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(result)


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
    cur.execute("CREATE EXTENSION pg_trgm;;")
    conn.commit()

    cur.execute("CREATE EXTENSION fuzzystrmatch;")
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"message": "Extensions turned on"}), 200


@app.route('/search/', methods=['GET'])
def search():
    html = """
        <form action="/search/" method="POST">
            Search term: <input type="text" name="search_term"><br>
            Search method: 
            <select name="search_method">
                <option value="SIMILARITY">SIMILARITY</option>
                <option value="SOUNDEX">SOUNDEX</option>
                <option value="LEVENSHTEIN">LEVENSHTEIN</option>
            </select><br>
            <input type="submit" value="Submit">
        </form>
        """
    return render_template_string(html)


@app.route('/search/', methods=['POST'])
def search_post():
    if not request.form['search_term']:
        return jsonify({"message": "Search term is required"}), 400
    if not request.form['search_method']:
        return jsonify({"message": "Search method is required"}), 400
    if request.form['search_method'] not in ['SIMILARITY', 'SOUNDEX', 'LEVENSHTEIN']:
        return jsonify({"message": "Invalid search method"}), 400

    if request.form['search_method'] == 'SIMILARITY':
        result = similarity_search(request.form['search_term'])
    elif request.form['search_method'] == 'SOUNDEX':
        result = soundex_search(request.form['search_term'])
    elif request.form['search_method'] == 'LEVENSHTEIN':
        result = levenshtein_search(request.form['search_term'])

    return jsonify(result), 200


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


if __name__ == '__main__':
    app.run(host='0.0.0.0')
