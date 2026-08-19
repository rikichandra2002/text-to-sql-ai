from dotenv import load_dotenv
load_dotenv()

import os
import sqlite3
import hashlib
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

metadata_collection = chroma_client.get_or_create_collection(
    name="database_metadata"
)

# ==========================================
# Get Metadata Collection for Uploaded DB
# ==========================================

def get_uploaded_metadata_collection(database_bytes):
    database_hash = hashlib.md5(
        database_bytes
    ).hexdigest()[:12]

    collection_name = (
        f"database_metadata_{database_hash}"
    )

    collection = chroma_client.get_or_create_collection(
        name=collection_name
    )

    return collection
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
# Retrieve Relevant Metadata from ChromaDB
# ==========================================

def retrieve_relevant_metadata(
    question,
    metadata_collection,
    n_results=3
):

    results = metadata_collection.query(
        query_texts=[question],
        n_results=n_results,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not documents:
        return None

    RELEVANCE_THRESHOLD = 1.8

    relevant_documents = []

    print("\n========== METADATA RETRIEVAL ==========")
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

    print("========================================\n")

    if not relevant_documents:
        return None

    return "\n\n".join(relevant_documents)
# ==========================================
# Function to Get Gemini Response with Metadata RAG
# ==========================================

def get_gemini_response(
    question,
    prompt,
    metadata_collection
):

    # Retrieve relevant metadata from ChromaDB
    relevant_metadata = retrieve_relevant_metadata(
    question,
    metadata_collection
)

    if relevant_metadata is None:
        return None

    # Generate SQL using Gemini
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[
            prompt[0],
            f"""
Relevant database metadata retrieved from the metadata knowledge base:

{relevant_metadata}

User question:

{question}
"""
        ]
    )

    return response.text.strip()

# ==========================================
# Validate Generated SQL Query
# ==========================================

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
# Build Metadata for Uploaded Database
# ==========================================

def build_uploaded_database_metadata(db):

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

    # Semantic aliases for the uploaded student database
    table_aliases = {
        "togrenciler": [
            "student",
            "students",
            "student records",
            "student information",
            "learners",
            "pupils"
        ],
        "tdersler": [
            "course",
            "courses",
            "subjects",
            "classes",
            "lessons"
        ],
        "tbolumler": [
            "department",
            "departments",
            "branch",
            "academic department"
        ],
        "tfakulteler": [
            "faculty",
            "faculties",
            "school",
            "college"
        ],
        "tkullanicilar": [
            "user",
            "users",
            "people",
            "persons",
            "user records"
        ],
        "tiller": [
            "city",
            "cities",
            "province",
            "provinces"
        ],
        "tilceler": [
            "district",
            "districts",
            "county",
            "counties"
        ],
        "tkangruplari": [
            "blood group",
            "blood groups",
            "blood type",
            "blood types"
        ],
        "tdersialanogrenciler": [
            "student courses",
            "students taking courses",
            "course enrollments",
            "enrollments",
            "student enrollment"
        ],
        "tyazokuluucretleri": [
            "summer school",
            "summer school fees",
            "school fees",
            "tuition fees",
            "summer course fees"
        ]
    }

    metadata = {}

    for table in tables:

        table_name = table[0]

        columns = cursor.execute(
            f"PRAGMA table_info('{table_name}')"
        ).fetchall()

        normalized_table_name = table_name.lower()

        table_metadata = {
            "table_name": table_name,
            "description": "",
            "keywords": [
                normalized_table_name
            ],
            "columns": {},
            "foreign_keys": []
        }

        # Add semantic aliases
        if normalized_table_name in table_aliases:

            table_metadata["keywords"].extend(
                table_aliases[normalized_table_name]
            )

        # Column metadata
        for column in columns:

            column_name = column[1]
            data_type = column[2]
            primary_key = bool(column[5])

            table_metadata["columns"][column_name] = {
                "type": data_type,
                "primary_key": primary_key
            }

            table_metadata["keywords"].append(
                column_name.lower()
            )

        # Foreign keys
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
# Create Metadata Documents
# ==========================================

def create_uploaded_metadata_documents(metadata):

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
# Text-to-SQL Prompt
# ==========================================

prompt = [
    """
    You are an expert in converting natural language questions into SQL queries.

    Your task is to convert the user's natural language question into a valid
    SQLite SQL query using ONLY the tables and columns provided in the
    relevant database metadata retrieved from the metadata knowledge base.

    IMPORTANT RULES:

    1. Return only the SQL query.
    2. Do not include any explanation or additional text.
    3. Do not use Markdown code fences such as ```sql or ``` around the query.
    4. Do not include the word "SQL" before or after the query.
    5. Generate only valid SQLite SQL syntax.
    6. Use only tables that exist in the provided metadata.
    7. Use only columns that exist in the provided metadata.
    8. Do not invent tables, columns, relationships, or values.
    9. Make sure the generated query directly answers the user's question.
    10. Return exactly ONE SQL statement.
    11. Return a SELECT query only.
    12. Do not perform INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
        or any other database modification operation.
    13. If the question cannot be answered using the provided metadata,
        return:
        SELECT 'Unable to answer from the available schema';

    The relevant database metadata will be provided separately along with
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
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ==========================================
# Custom CSS
# ==========================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ==========================================
   GLOBAL APP
   ========================================== */

.stApp {

    background:
        radial-gradient(
            circle at 10% 10%,
            rgba(124, 58, 237, 0.22),
            transparent 30%
        ),
        radial-gradient(
            circle at 90% 20%,
            rgba(6, 182, 212, 0.18),
            transparent 30%
        ),
        radial-gradient(
            circle at 50% 100%,
            rgba(168, 85, 247, 0.14),
            transparent 35%
        ),
        #070816;

    color: #f8fafc;

    font-family: 'Inter', sans-serif;
}


/* ==========================================
   MAIN CONTAINER
   ========================================== */

.block-container {

    max-width: 1100px;

    padding-top: 3rem;
    padding-bottom: 4rem;
}


/* ==========================================
   TITLE
   ========================================== */

.title {

    text-align: center;

    font-size: 56px;

    font-weight: 800;

    letter-spacing: -1.5px;

    background:
        linear-gradient(
            90deg,
            #a78bfa,
            #22d3ee,
            #c084fc
        );

    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;

    margin-bottom: 8px;

    text-shadow:
        0 0 30px rgba(139, 92, 246, 0.20);
}


/* ==========================================
   SUBTITLE
   ========================================== */

.subtitle {

    text-align: center;

    font-size: 18px;

    color: #94a3b8;

    margin-bottom: 30px;

    letter-spacing: 0.2px;
}


/* ==========================================
   INFORMATION BOX
   ========================================== */

[data-testid="stAlert"] {

    border-radius: 18px !important;

    border: 1px solid rgba(139, 92, 246, 0.30) !important;

    background:
        linear-gradient(
            135deg,
            rgba(124, 58, 237, 0.14),
            rgba(6, 182, 212, 0.08)
        ) !important;

    box-shadow:
        0 10px 35px rgba(0, 0, 0, 0.20);

}


/* ==========================================
   FILE UPLOADER
   ========================================== */

[data-testid="stFileUploader"] {

    background:
        rgba(255, 255, 255, 0.045);

    border:
        1px solid rgba(139, 92, 246, 0.35);

    border-radius:
        20px;

    padding:
        12px;

    box-shadow:
        0 10px 40px rgba(0, 0, 0, 0.25),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
}


/* ==========================================
   TEXT INPUT
   ========================================== */

[data-testid="stTextInput"] input {

    background:
        rgba(255, 255, 255, 0.055) !important;

    color:
        #ffffff !important;

    border:
        1px solid rgba(139, 92, 246, 0.35) !important;

    border-radius:
        14px !important;

    padding:
        15px 18px !important;

    font-size:
        16px !important;

    transition:
        all 0.25s ease;
}


[data-testid="stTextInput"] input:focus {

    border-color:
        #8b5cf6 !important;

    box-shadow:
        0 0 0 2px rgba(139, 92, 246, 0.15),
        0 0 25px rgba(139, 92, 246, 0.25);
}


/* ==========================================
   BUTTONS
   ========================================== */

.stButton > button {

    width:
        100%;

    border-radius:
        14px;

    border:
        1px solid rgba(139, 92, 246, 0.50);

    background:
        linear-gradient(
            135deg,
            #7c3aed,
            #06b6d4
        );

    color:
        #ffffff;

    font-weight:
        700;

    padding:
        12px 20px;

    transition:
        transform 0.2s ease,
        box-shadow 0.2s ease;
}


.stButton > button:hover {

    transform:
        translateY(-2px);

    box-shadow:
        0 10px 30px rgba(124, 58, 237, 0.35),
        0 0 25px rgba(6, 182, 212, 0.20);
}


/* ==========================================
   EXPANDERS
   ========================================== */

[data-testid="stExpander"] {

    background:
        rgba(255, 255, 255, 0.035);

    border:
        1px solid rgba(139, 92, 246, 0.25);

    border-radius:
        18px;

    margin-bottom:
        10px;

    box-shadow:
        0 8px 30px rgba(0, 0, 0, 0.18);
}


/* ==========================================
   CODE BLOCKS
   ========================================== */

pre {

    background:
        linear-gradient(
            135deg,
            rgba(15, 23, 42, 0.95),
            rgba(30, 27, 75, 0.95)
        ) !important;

    border:
        1px solid rgba(139, 92, 246, 0.25);

    border-radius:
        16px;

    box-shadow:
        0 8px 30px rgba(0, 0, 0, 0.25);
}


/* ==========================================
   SUCCESS / WARNING BOXES
   ========================================== */

[data-testid="stAlert"] {

    border-radius:
        16px !important;

    box-shadow:
        0 8px 30px rgba(0, 0, 0, 0.18);
}


/* ==========================================
   SCROLLBAR
   ========================================== */

::-webkit-scrollbar {

    width:
        8px;
}


::-webkit-scrollbar-track {

    background:
        #070816;
}


::-webkit-scrollbar-thumb {

    background:
        linear-gradient(
            #7c3aed,
            #06b6d4
        );

    border-radius:
        10px;
}


/* ==========================================
   BACKGROUND GLOW
   ========================================== */

.stApp::before {

    content:
        "";

    position:
        fixed;

    width:
        500px;

    height:
        500px;

    top:
        -250px;

    left:
        -200px;

    background:
        rgba(124, 58, 237, 0.12);

    filter:
        blur(100px);

    border-radius:
        50%;

    pointer-events:
        none;

    z-index:
        0;
}


.stApp::after {

    content:
        "";

    position:
        fixed;

    width:
        450px;

    height:
        450px;

    bottom:
        -250px;

    right:
        -150px;

    background:
        rgba(6, 182, 212, 0.10);

    filter:
        blur(100px);

    border-radius:
        50%;

    pointer-events:
        none;

    z-index:
        0;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# Application Title
# ==========================================

st.markdown(
    '<div class="title">🧠 Text-to-SQL AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Talk to your database using plain English'
    '</div>',
    unsafe_allow_html=True
)

# ==========================================
# Information Box
# ==========================================

st.info(
    "💡 Try asking: "
    "\"Show all students in Data Science\"  •  "
    "\"Who scored more than 80 marks?\"  •  "
    "\"What is the average marks?\""
)
# ==========================================
# Database Upload
# ==========================================

st.subheader("📁 Upload Your SQLite Database")

uploaded_db = st.file_uploader(
    "Upload a SQLite database",
    type=["db", "sqlite", "sqlite3"]
)

# ==========================================
# Uploaded Database State
# ==========================================

uploaded_metadata_collection = None
database_path = None

if uploaded_db is not None:

    database_path = "uploaded_database.db"
    uploaded_metadata_collection = get_uploaded_metadata_collection(
    uploaded_db.getvalue()
)

    with open(database_path, "wb") as f:
        f.write(uploaded_db.getbuffer())

    st.success(
        f"Database uploaded: {uploaded_db.name}"
    )

    # Analyze uploaded database
    uploaded_metadata = build_uploaded_database_metadata(
        database_path
    )

    uploaded_documents = create_uploaded_metadata_documents(
        uploaded_metadata
    )

    st.subheader("🔍 Database Metadata")

    st.write(
        f"Tables discovered: {len(uploaded_metadata)}"
    )

    for document in uploaded_documents:

        with st.expander(
            f"📋 {document['table_name']}"
        ):

            st.code(
                document["text"]
            )

    # Create database-specific collection
    uploaded_metadata_collection = get_uploaded_metadata_collection(
    uploaded_db.getvalue()
)

    for document in uploaded_documents:

        uploaded_metadata_collection.upsert(
            ids=[document["table_name"]],
            documents=[document["text"]],
            metadatas=[
                {
                    "table_name": document["table_name"]
                }
            ]
        )

    st.success(
        "Database metadata indexed successfully."
    )

    print("\n========== UPLOADED DATABASE RAG ==========")

    print(
        "Collection:",
        uploaded_metadata_collection.name
    )

    print(
        "Documents:",
        uploaded_metadata_collection.count()
    )

    print("===========================================\n")
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

        st.warning(
            "⚠️ Please enter a question first."
        )

    elif uploaded_metadata_collection is None:

        st.warning(
            "⚠️ Please upload a SQLite database first."
        )

    else:

        # ==========================================
        # Generate SQL
        # ==========================================

        with st.spinner("🤖 Generating SQL query..."):

            try:

                response = get_gemini_response(
                    question,
                    prompt,
                    uploaded_metadata_collection
                )
                print("\n========== GENERATED SQL ==========")
                print(response)
                print("===================================\n")

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
    database_path
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