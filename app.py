from dotenv import load_dotenv
load_dotenv()

import os
import sqlite3
import streamlit as st
import sqlglot
from sqlglot import exp
import chromadb
from google import genai


# ==========================================
# Gemini API Configuration
# ==========================================

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# ==========================================
# ChromaDB Configuration
# ==========================================

chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

schema_collection = chroma_client.get_or_create_collection(
    name="database_schema"
)
# ==========================================
# Retrieve Relevant Schema from ChromaDB
# ==========================================

def retrieve_relevant_schema(question, n_results=3):

    results = schema_collection.query(
        query_texts=[question],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not documents:
        return None

    # Experimental relevance threshold
    RELEVANCE_THRESHOLD = 1.8

    relevant_documents = []

    print("\n========== RAG RETRIEVAL ==========")
    print("User Question:", question)

    for i, document in enumerate(documents):

        table_name = metadatas[i].get("table_name")
        distance = distances[i]

        print(f"\nResult {i + 1}")
        print("Table:", table_name)
        print("Distance:", distance)

        if distance <= RELEVANCE_THRESHOLD:

            print("Status: RELEVANT")

            relevant_documents.append(document)

        else:

            print("Status: NOT RELEVANT")

    print("===================================\n")

    if not relevant_documents:
        return None

    return "\n\n".join(relevant_documents)
# ==========================================
# Function to Get Gemini Response with RAG
# ==========================================

def get_gemini_response(question, prompt):

    # Retrieve relevant schema from ChromaDB
    relevant_schema = retrieve_relevant_schema(question)
    if relevant_schema is None:
        return None
    # Generate SQL using Gemini
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[
            prompt[0],
            f"""
Relevant database schema retrieved from the schema knowledge base:

{relevant_schema}

User question:

{question}
"""
        ]
    )

    return response.text.strip()
def validate_sql_query(sql):

    try:

        # Parse all SQL statements
        statements = sqlglot.parse(
            sql,
            dialect="sqlite"
        )

        # Block empty SQL
        if not statements:
            return False, "Empty SQL query."

        # Allow only one SQL statement
        if len(statements) != 1:
            return False, "Multiple SQL statements are not allowed."

        parsed = statements[0]

        # Allow only SELECT statements
        if not isinstance(parsed, exp.Select):
            return False, "Only SELECT queries are allowed."

        return True, "SQL query is safe."

    except Exception as e:

        return False, f"Invalid SQL query: {e}"
# ==========================================
# Function to Execute SQL Query
# ==========================================

def read_sql_query(sql, db):

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    cur.execute(sql)

    rows = cur.fetchall()

    conn.close()

    return rows

# ==========================================
# Function to Get Detailed Database Schema
# ==========================================

def get_database_schema(db):

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    # Get all tables
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    schema = {}

    for table in tables:

        table_name = table[0]

        # Get detailed information about columns
        columns = cursor.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        schema[table_name] = {
            "columns": {}
        }

        for column in columns:

            column_id = column[0]
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
# Format Detailed Schema for Gemini
# ==========================================

def format_schema_for_prompt(schema):

    schema_text = ""

    for table_name, table_info in schema.items():

        schema_text += f"Table: {table_name}\n"

        schema_text += "Columns:\n"

        for column_name, column_info in table_info["columns"].items():

            data_type = column_info["type"]
            primary_key = column_info["primary_key"]

            schema_text += (
                f"- {column_name} "
                f"(Type: {data_type}, "
                f"Primary Key: {primary_key})\n"
            )

        schema_text += "\n"

    return schema_text
# ==========================================
# Get Database Schema
# ==========================================

database_schema = get_database_schema("student.db")

schema_text = format_schema_for_prompt(database_schema)
# ==========================================
# Text-to-SQL Prompt
# ==========================================

prompt = [
    """
    You are an expert in converting natural language questions into SQL queries.

    Your task is to convert the user's natural language question into a valid
    SQLite SQL query using ONLY the tables and columns provided in the
    relevant database schema retrieved from the schema knowledge base.

    IMPORTANT RULES:

    1. Return only the SQL query.
    2. Do not include any explanation or additional text.
    3. Do not use Markdown code fences such as ```sql or ``` around the query.
    4. Do not include the word "SQL" before or after the query.
    5. Generate only valid SQLite SQL syntax.
    6. Use only tables that exist in the provided database schema.
    7. Use only columns that exist in the provided database schema.
    8. Do not invent tables, columns, relationships, or values.
    9. Make sure the generated query directly answers the user's question.
    10. Return exactly ONE SQL statement.
    11. Return a SELECT query only.
    12. Do not perform INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
        or any other database modification operation.
    13. If the question cannot be answered using the provided schema,
        return a safe SELECT query only if possible; otherwise return:
        SELECT 'Unable to answer from the available schema';

    The relevant database schema will be provided separately along with
    the user's question.

    Now convert the user's natural language question into the appropriate
    SQLite SQL query.
    """
]

# ==========================================
# Streamlit Page Configuration
# ==========================================

st.set_page_config(
    page_title="Text-to-SQL AI",
    page_icon="🧠",
    layout="centered"
)


# ==========================================
# Custom CSS
# ==========================================

st.markdown(
    """
    <style>

    .main {
        padding-top: 2rem;
    }

    .title {
        text-align: center;
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        font-size: 18px;
        margin-bottom: 30px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================
# Application Title
# ==========================================

st.markdown(
    '<div class="title">🧠 Text-to-SQL AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Ask questions about your student database in plain English'
    '</div>',
    unsafe_allow_html=True
)


# ==========================================
# Information Box
# ==========================================

st.info(
    "💡 Try questions like: "
    "'Show all students in Data Science' or "
    "'Who scored more than 80 marks?'"
)


# ==========================================
# User Input
# ==========================================

question = st.text_input(
    "🔎 Enter your question",
    placeholder="e.g. Show all students studying Data Science",
    key="input"
)


# ==========================================
# Submit Button
# ==========================================

submit = st.button(
    "🚀 Ask the Question",
    use_container_width=True
)


# ==========================================
# Process User Question
# ==========================================

if submit:

    if not question.strip():

        st.warning("⚠️ Please enter a question first.")

    else:

        # --------------------------------------
        # Generate SQL using Gemini
        # --------------------------------------

        with st.spinner("🤖 Generating SQL query..."):

            try:

                response = get_gemini_response(
                    question,
                    prompt
                )

            except Exception as e:

                st.error(
                    f"❌ Error while communicating with Gemini: {e}"
                )

                st.stop()


        # --------------------------------------
        # Check if relevant schema was found
        # --------------------------------------

        if response is None:

            st.warning(
                "⚠️ I could not find a sufficiently relevant "
                "database schema for this question."
            )

            st.stop()


        # --------------------------------------
        # Validate Generated SQL
        # --------------------------------------

        is_valid, message = validate_sql_query(response)

        if not is_valid:

            st.error(
                f"🛡️ SQL query blocked: {message}"
            )

            st.stop()

        # --------------------------------------
        # Display Validated SQL
        # --------------------------------------

        st.subheader("📝 Generated SQL Query")

        st.code(
            response,
            language="sql"
        )

        # --------------------------------------
        # Execute SQL Query
        # --------------------------------------

        with st.spinner("🔍 Fetching results from database..."):

            try:

                data = read_sql_query(
                    response,
                    "student.db"
                )

            except Exception as e:

                st.error(
                    f"❌ Error while executing SQL query: {e}"
                )

                st.stop()


        # --------------------------------------
        # Display Results
        # --------------------------------------

        st.subheader("📊 Query Results")

        if data:

            for row in data:

                st.write(row)

        else:

            st.info("No records found.")