# Fuzzy Search with Postgres and Qdrant vector database - comparison

The purpose of this repo is to test fuzzy search in Postgres and Qdrant vector database.

The names were generated to contain various versions of the same name, e.g.: 
- John Smith
- John Shmith
- ...

We are testing three methods of fuzzy search in Postrgres:
- Trigrams (Similarity)
- Soundex
- Levenshtein distance

Using Qdrant vector database we are testing the "distance between names".
They are first embedded using open source `all-mpnet-base-v2` model available on [here](https://huggingface.co/sentence-transformers/all-mpnet-base-v2).
Due to the way the embedding works, once the very similar names are found, there 
are also names from a particular language group presented. 

## How to run

```bash
docker-compose up
```

Please note that the first run will take a while, 
as there is a few gigabytes of data to download. Also, the first
upsert to Qdrant will take a while, as the model has to be
downloaded and the index needs to be built.

---

## Developer notes

### New packages in `requirements.txt`

When you change your `requirements.txt` file, you'll need to rebuild your Docker image to install the new Python packages. 

Here are the steps:

1. Stop the running Docker containers with the following command:

    ```bash
    docker-compose down
    ```

2. Then rebuild and start your Docker containers:

    ```bash
    docker-compose up --build
    ```

### Postrgres related notes

#### Trigrams:

```sql
CREATE EXTENSION pg_trgm;
```

usage:

```sql
SELECT
	*
FROM names
WHERE SIMILARITY(combined_name, 'John Smith') > 0.4 ;
```

#### Phonetic matching:

```sql
CREATE EXTENSION fuzzystrmatch;
```

usage: 

```sql
SELECT
	*
FROM names
WHERE SOUNDEX(combined_name) = SOUNDEX('John Smith');
```

```sql
SELECT
	*
FROM names
ORDER BY SIMILARITY(
	METAPHONE(combined_name,10),
    METAPHONE('John Smith',10)
    ) DESC
LIMIT 5;
```

#### Levenshtein distance:

```sql
SELECT
	*,
    LEVENSHTEIN(combined_name, 'John Smith')
FROM names
ORDER BY LEVENSHTEIN(combined_name, 'John Smith') ASC
LIMIT 5
```