import sqlite3

## Connect to the SQLite database
connection = sqlite3.connect('student.db') 

## Create a cursor object to execute SQL commands
cursor = connection.cursor()

### Create a table named 'students' if it doesn't exist
table_info = """
Create table STUDENT(NAME VARCHAR (25), CLASS VARCHAR (25),SECTION VARCHAR (25),MARKS INT);

"""

cursor.execute(table_info)

## Insert Some more records

cursor.execute('''Insert Into STUDENT values('Krish','Data Science','A',90)''')
cursor.execute('''Insert Into STUDENT values('Sudhanshu','Data Science','B',100)''')
cursor.execute('''Insert Into STUDENT values('Darius','Data Science','B',86)''')
cursor.execute('''Insert Into STUDENT values('Vikash','DEVOPS','A',50)''')
cursor.execute('''Insert Into STUDENT values('Dipesh','DEVOPS','A',35)''')

#Display all the records from the STUDENT table
print("All records from the STUDENT table:")

data = cursor.execute('''Select * from STUDENT''')

for row in data:
    print(row)

## Close the cursor and connection to the database
connection.commit()
connection.close()
