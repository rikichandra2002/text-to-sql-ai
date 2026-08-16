# 🧠 Text-to-SQL AI

An AI-powered **Natural Language → SQL** application that lets users
upload their own SQLite database and ask questions about it in plain
English.

The system combines **Gemini, ChromaDB, Retrieval-Augmented Generation
(RAG), SQLGlot, SQLite, and Streamlit** to retrieve relevant database
metadata, generate schema-aware SQL, validate the generated query,
execute it, and display the results.

## 🚀 Live Demo

**Streamlit App:**\
https://rikichandra2002-text-to-sql-ai-app-v9z9wf.streamlit.app/

**GitHub Repository:**\
https://github.com/rikichandra2002/text-to-sql-ai

------------------------------------------------------------------------

## ✨ Features

-   📁 Upload your own SQLite database
-   🔍 Automatically discover tables and columns
-   🔑 Extract primary-key and foreign-key metadata
-   🧠 Convert database metadata into searchable RAG documents
-   🗂️ Store metadata in ChromaDB
-   🎯 Retrieve only relevant metadata using semantic similarity
-   🤖 Generate SQLite SQL using Gemini
-   🛡️ Validate generated SQL with SQLGlot
-   🔒 Allow only a single `SELECT` statement
-   ⚠️ Reject questions when sufficiently relevant database metadata
    cannot be found
-   ▶️ Execute validated SQL against the uploaded SQLite database
-   📊 Display query results in Streamlit
-   🎨 Responsive dark UI with custom styling

------------------------------------------------------------------------

# 🏗️ How It Works

The application follows this pipeline:

``` mermaid
flowchart TD

    A[👤 User] --> B[🌐 Streamlit UI]

    B --> C[📁 Upload SQLite Database]

    C --> D[💾 Temporary Uploaded Database]

    D --> E[🔍 Metadata Extraction]

    E --> E1[Tables]
    E --> E2[Columns + Data Types]
    E --> E3[Primary Keys]
    E --> E4[Foreign Keys]
    E --> E5[Keywords]

    E1 --> F[📝 Metadata Documents]
    E2 --> F
    E3 --> F
    E4 --> F
    E5 --> F

    F --> G[🗂️ ChromaDB]

    G --> H[Database-Specific Metadata Collection]

    B --> I[❓ Natural Language Question]

    I --> J[🔎 Semantic Metadata Retrieval]

    H --> J

    J --> K{Relevant Metadata Found?}

    K -- No --> L[⚠️ Stop and Ask for a Relevant Database Question]

    K -- Yes --> M[📚 Retrieved Metadata + User Question]

    M --> N[🤖 Gemini]

    N --> O[📝 Generated SQLite SQL]

    O --> P[🛡️ SQLGlot Validation]

    P --> Q{Valid Single SELECT?}

    Q -- No --> R[🚫 Block Query]

    Q -- Yes --> S[🗄️ Execute SQL on SQLite]

    S --> T[📊 Query Results]

    T --> B
```

### Pipeline in simple terms

**1. User uploads a database**

The Streamlit interface accepts `.db`, `.sqlite`, and `.sqlite3` files.

**2. Database metadata is extracted**

The application reads SQLite system metadata and discovers:

-   Table names
-   Column names
-   Data types
-   Primary keys
-   Foreign keys
-   Search keywords

**3. Metadata becomes RAG documents**

Each table is represented as a searchable text document containing its
metadata.

**4. Metadata is stored in ChromaDB**

The application creates a database-specific ChromaDB collection so the
uploaded database has its own metadata knowledge base.

**5. User asks a natural-language question**

For example:

> Who scored more than 80 marks?

**6. Relevant metadata is retrieved**

The question is compared against the metadata documents using ChromaDB
semantic retrieval.

The application currently uses a relevance distance threshold of
**1.8**.

If no sufficiently relevant metadata is found, SQL generation stops.

**7. Gemini generates SQL**

The retrieved metadata and the user's question are supplied to Gemini.

Gemini is instructed to:

-   Use only retrieved tables and columns
-   Generate valid SQLite syntax
-   Return exactly one SQL statement
-   Return a `SELECT` query only
-   Avoid database modification operations

Example:

``` sql
SELECT NAME FROM STUDENT WHERE MARKS > 80;
```

**8. SQLGlot validates the generated query**

The query is parsed using SQLGlot with the SQLite dialect.

The validation layer rejects:

-   Empty queries
-   Multiple statements
-   Non-`SELECT` statements
-   Invalid SQL

**9. Valid SQL is executed**

The validated query is executed against the uploaded SQLite database.

**10. Results are displayed**

The returned rows are displayed through the Streamlit interface.

------------------------------------------------------------------------

# 🧠 Architecture

The core architecture can be summarized as:

``` text
                    ┌──────────────────────┐
                    │        User          │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Streamlit UI      │
                    └──────────┬───────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
        ┌──────────────────┐      ┌──────────────────┐
        │ Upload SQLite DB │      │ Natural Language │
        └────────┬─────────┘      │    Question      │
                 │                └────────┬─────────┘
                 ▼                         │
        ┌──────────────────┐               │
        │ Metadata         │               │
        │ Extraction       │               │
        └────────┬─────────┘               │
                 │                         │
                 ▼                         │
        ┌──────────────────┐               │
        │ Metadata         │               │
        │ Documents        │               │
        └────────┬─────────┘               │
                 │                         │
                 ▼                         │
        ┌──────────────────┐               │
        │    ChromaDB      │◄──────────────┘
        │   Metadata RAG   │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Relevant Schema  │
        │ / Metadata       │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │      Gemini      │
        │   SQL Generation │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │     SQLGlot      │
        │  Safety Checker  │
        └────────┬─────────┘
                 │
            Valid SELECT?
                 │
                 ▼
        ┌──────────────────┐
        │  SQLite Query    │
        │    Execution     │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │   Query Results  │
        └──────────────────┘
```

------------------------------------------------------------------------

# 🛡️ SQL Safety Layer

The application does **not** directly execute whatever Gemini returns.

Before execution, the generated SQL passes through SQLGlot validation.

The validator:

1.  Parses the SQL using the SQLite dialect
2.  Rejects empty SQL
3.  Rejects multiple SQL statements
4.  Allows only `SELECT`
5.  Blocks database modification statements such as:

``` sql
INSERT
UPDATE
DELETE
DROP
ALTER
CREATE
```

This creates a basic safety boundary between the LLM and the database.

> This is a project-level safety layer, not a complete production
> database security system.

------------------------------------------------------------------------

# 🗂️ Project Structure

``` text
text-to-sql-ai/
│
├── app.py
│   └── Main Streamlit application
│       ├── Database upload
│       ├── Metadata extraction
│       ├── ChromaDB retrieval
│       ├── Gemini SQL generation
│       ├── SQL validation
│       ├── SQLite execution
│       └── Result display
│
├── metadata_linking.py
│   └── Metadata extraction and ChromaDB indexing
│       for the sample database
│
├── schema_rag.py
│   └── Earlier schema-RAG implementation and
│       retrieval experiments
│
├── schema_test.py
│   └── Schema/RAG testing utility
│
├── sql.py
│   └── Creates/populates the sample STUDENT database
│
├── student.db
│   └── Small demo SQLite database
│
├── requirements.txt
│   └── Python dependencies
│
├── .gitignore
│   └── Prevents secrets, environments, caches,
│       and temporary databases from being committed
│
└── README.md
    └── Project documentation
```

------------------------------------------------------------------------

# 🛠️ Tech Stack

  Technology      Purpose
  --------------- --------------------------------------
  Python          Application logic
  Streamlit       Web interface
  Google Gemini   Natural-language-to-SQL generation
  ChromaDB        Vector database / metadata retrieval
  RAG             Relevant schema/metadata retrieval
  SQLGlot         SQL parsing and validation
  SQLite          Database engine
  python-dotenv   Local environment-variable loading

------------------------------------------------------------------------

# ⚙️ Local Setup

## 1. Clone the repository

``` bash
git clone https://github.com/rikichandra2002/text-to-sql-ai.git
cd text-to-sql-ai
```

## 2. Create a virtual environment

### Windows

``` powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### macOS / Linux

``` bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

``` bash
pip install -r requirements.txt
```

## 4. Configure Gemini

Create a `.env` file in the project root:

``` env
GEMINI_API_KEY=your_gemini_api_key
```

Never commit `.env` to GitHub.

## 5. Run the application

``` bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

------------------------------------------------------------------------

# ☁️ Streamlit Cloud Deployment

The project can be deployed using Streamlit Community Cloud.

1.  Push the repository to GitHub.
2.  Create a new Streamlit Cloud application.
3.  Select:
    -   Repository: `rikichandra2002/text-to-sql-ai`
    -   Branch: `main`
    -   Main file: `app.py`
4.  Add the Gemini API key through Streamlit Cloud Secrets.

Use:

``` toml
GEMINI_API_KEY = "your_gemini_api_key"
```

Do not place the API key inside the GitHub repository.

------------------------------------------------------------------------

# 🧪 Example

Using the included sample `STUDENT` database:

### Question

``` text
Who scored more than 80 marks?
```

### Retrieved metadata

``` text
Table: STUDENT

Columns:
- NAME
- CLASS
- SECTION
- MARKS
```

### Generated SQL

``` sql
SELECT NAME FROM STUDENT WHERE MARKS > 80;
```

### Result

``` text
Krish
Sudhanshu
Darius
```

------------------------------------------------------------------------

# 📁 Using Your Own Database

The application is not limited to the included `student.db`.

Upload your own SQLite database through:

``` text
📁 Upload Your SQLite Database
```

The application then:

``` text
Your Database
      ↓
Discover Tables
      ↓
Extract Metadata
      ↓
Create Metadata Documents
      ↓
Index in ChromaDB
      ↓
Ask Natural-Language Question
      ↓
Retrieve Relevant Metadata
      ↓
Gemini Generates SQL
      ↓
SQLGlot Validates SQL
      ↓
Execute on Uploaded SQLite DB
      ↓
Display Results
```

This makes the application reusable across different SQLite database
schemas.

------------------------------------------------------------------------

# 🔐 Security Considerations

The project includes several basic protections:

-   Gemini API keys are kept outside source code
-   `.env` is excluded from Git
-   Uploaded database files are excluded from Git
-   Generated SQL is parsed before execution
-   Only one SQL statement is allowed
-   Only `SELECT` queries are accepted
-   Queries without sufficiently relevant metadata are stopped

For production systems, additional controls would be recommended,
including:

-   Database user permissions
-   Query timeouts
-   Result-size limits
-   Resource isolation
-   Authentication and authorization
-   Persistent multi-user storage
-   Audit logging
-   Stronger SQL policy enforcement

------------------------------------------------------------------------

# ⚠️ Current Limitations

This project is intentionally a practical learning/portfolio
implementation.

Current limitations include:

-   SQLite is the supported database engine
-   SQL generation depends on the Gemini model
-   Semantic relevance uses a fixed distance threshold
-   ChromaDB is currently local/persistent storage
-   No user authentication system
-   No production-grade multi-tenant isolation
-   Uploaded databases are processed through a temporary local file
-   Complex schemas may require richer metadata descriptions or examples

------------------------------------------------------------------------

# 🔮 Future Improvements

Possible next improvements include:

-   PostgreSQL / MySQL support
-   Better schema descriptions and business synonyms
-   Column-level schema linking
-   Query-result summarization
-   SQL generation retry/refinement
-   Query execution timeouts
-   Result pagination
-   Authentication
-   Persistent cloud vector storage
-   Multi-user database isolation
-   Query history
-   Database relationship visualization
-   Evaluation dataset and Text-to-SQL accuracy benchmarking

------------------------------------------------------------------------

# 🎯 Learning Outcomes

This project demonstrates practical experience with:

-   Retrieval-Augmented Generation
-   Vector databases
-   Semantic search
-   Schema/metadata linking
-   LLM prompting
-   Natural-language-to-SQL generation
-   SQL parsing and validation
-   SQLite database interaction
-   Streamlit application development
-   Environment/secrets management
-   Git/GitHub
-   Cloud deployment

------------------------------------------------------------------------

## 👨‍💻 Author

**Ritwik Chandra**

B.Tech --- Artificial Intelligence & Machine Learning

GitHub:\
https://github.com/rikichandra2002

------------------------------------------------------------------------

## ⭐ Project

If this project is useful or interesting, consider giving the repository
a ⭐ on GitHub.

**Repository:**\
https://github.com/rikichandra2002/text-to-sql-ai
