import sqlite3


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


schema = get_database_schema("student.db")

print("DATABASE METADATA:")
print(schema)

print("\nFORMATTED SCHEMA:")
print(format_schema_for_prompt(schema))