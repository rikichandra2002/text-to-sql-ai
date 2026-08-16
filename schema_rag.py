import sqlite3
import chromadb


# ==========================================
# Get Database Schema
# ==========================================

def get_database_schema(db):

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    schema = {}

    for table in tables:

        table_name = table[0]

        columns = cursor.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        schema[table_name] = {
            "columns": {}
        }

        for column in columns:

            column_name = column[1]
            data_type = column[2]
            primary_key = column[5]

            schema[table_name]["columns"][column_name] = {
                "type": data_type,
                "primary_key": bool(primary_key)
            }

    conn.close()

    return schema


# ==========================================
# Convert Schema to RAG Documents
# ==========================================

def create_schema_documents(schema):

    documents = []

    for table_name, table_info in schema.items():

        document = f"Table: {table_name}\n"
        document += "Columns:\n"

        for column_name, column_info in table_info["columns"].items():

            document += (
                f"- {column_name} "
                f"(Type: {column_info['type']}, "
                f"Primary Key: {column_info['primary_key']})\n"
            )

        documents.append({
            "table_name": table_name,
            "text": document
        })

    return documents


# ==========================================
# Create ChromaDB Collection
# ==========================================

client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_or_create_collection(
    name="database_schema"
)


# ==========================================
# Store Schema Documents
# ==========================================

schema = get_database_schema("student.db")

documents = create_schema_documents(schema)

for document in documents:

    collection.upsert(
        ids=[document["table_name"]],
        documents=[document["text"]],
        metadatas=[
            {
                "table_name": document["table_name"]
            }
        ]
    )

print("Schema documents stored successfully.")


# ==========================================
# Test Multiple Retrieval Queries
# ==========================================

test_questions = [
    "Which students scored more than 80 marks?",
    "Show all students in Data Science.",
    "What is the average student marks?",
    "What is the weather in Kolkata today?"
]


for question in test_questions:

    results = collection.query(
        query_texts=[question],
        n_results=1,
        include=["documents", "metadatas", "distances"]
    )

    print("\n========================================")
    print("QUESTION:", question)

    if results["documents"][0]:

        print(
            "TABLE:",
            results["metadatas"][0][0]["table_name"]
        )

        print(
            "DISTANCE:",
            results["distances"][0][0]
        )

        print("SCHEMA:")
        print(results["documents"][0][0])

    else:

        print("NO RESULT")

print("========================================")