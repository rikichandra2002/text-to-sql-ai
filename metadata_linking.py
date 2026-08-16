import sqlite3
import chromadb


def build_metadata_dictionary(db):

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    tables = cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    metadata = {}

    for table in tables:

        table_name = table[0]

        columns = cursor.execute(
            f"PRAGMA table_info('{table_name}')"
        ).fetchall()

        table_metadata = {
            "table_name": table_name,
            "description": "",
            "keywords": [
                table_name.lower()
            ],
            "columns": {},
            "foreign_keys": []
        }

        for column in columns:

            column_name = column[1]
            data_type = column[2]
            primary_key = bool(column[5])

            table_metadata["columns"][column_name] = {
                "type": data_type,
                "primary_key": primary_key
            }

        for column in columns:

            column_name = column[1]

            table_metadata["keywords"].append(
                column_name.lower()
            )

        foreign_keys = cursor.execute(
            f"PRAGMA foreign_key_list('{table_name}')"
        ).fetchall()

        for foreign_key in foreign_keys:

            table_metadata["foreign_keys"].append({
                "column": foreign_key[3],
                "references_table": foreign_key[2],
                "references_column": foreign_key[4]
            })

        metadata[table_name] = table_metadata

    conn.close()

    return metadata
# ==========================================
# Convert Metadata to Searchable Documents
# ==========================================

def create_metadata_documents(metadata):

    documents = []

    for table_name, table_info in metadata.items():

        document = f"Table: {table_name}\n"

        document += (
            f"Description: "
            f"{table_info['description']}\n"
        )

        document += (
            f"Keywords: "
            f"{', '.join(table_info['keywords'])}\n"
        )

        document += "\nColumns:\n"

        for column_name, column_info in table_info["columns"].items():

            document += (
                f"- {column_name} "
                f"(Type: {column_info['type']}, "
                f"Primary Key: {column_info['primary_key']})\n"
            )

        document += "\nForeign Keys:\n"

        if table_info["foreign_keys"]:

            for foreign_key in table_info["foreign_keys"]:

                document += (
                    f"- {foreign_key['column']} → "
                    f"{foreign_key['references_table']}."
                    f"{foreign_key['references_column']}\n"
                )

        else:

            document += "- None\n"

        documents.append({
            "table_name": table_name,
            "text": document
        })

    return documents

# ==========================================
# Create ChromaDB Metadata Collection
# ==========================================

chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

metadata_collection = chroma_client.get_or_create_collection(
    name="database_metadata"
)
# ==========================================
# Build and Store Metadata Documents
# ==========================================

metadata = build_metadata_dictionary("student.db")

print("NUMBER OF TABLES:", len(metadata))

documents = create_metadata_documents(metadata)

for document in documents:

    metadata_collection.upsert(
        ids=[document["table_name"]],
        documents=[document["text"]],
        metadatas=[
            {
                "table_name": document["table_name"]
            }
        ]
    )

print("\nMetadata documents stored successfully.")

# ==========================================
# Test Metadata Retrieval
# ==========================================

test_question = "Which students scored more than 80 marks?"

results = metadata_collection.query(
    query_texts=[test_question],
    n_results=1,
    include=[
        "documents",
        "metadatas",
        "distances"
    ]
)

print("\n========== METADATA RETRIEVAL ==========")

print("Question:", test_question)

print(
    "Table:",
    results["metadatas"][0][0]["table_name"]
)

print(
    "Distance:",
    results["distances"][0][0]
)

print("Retrieved Metadata:")

print(
    results["documents"][0][0]
)

print("========================================")