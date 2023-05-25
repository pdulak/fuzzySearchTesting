from flask import Flask, jsonify, render_template_string
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

from flask import render_template_string

@app.route('/')
def home():
    html = """
    <p>Use the following links to interact with the database:</p>
    <ul>
        <li><a href="/test">Test DB connection</a></li>
        <li><a href="/create">Create the 'names' table</a></li>
        <li><a href="/initialize">Initialize the 'names' table</a></li>
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



if __name__ == '__main__':
    app.run(host='0.0.0.0')
