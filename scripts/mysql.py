import mysql.connector

# Database connection details
DB_HOST = "your_db_host"  # Replace with your database host address (e.g., localhost, 192.168.1.10)
DB_NAME = "your_db_name"  # Replace with your database name
DB_USER = "your_db_user"  # Replace with your database username
DB_PASSWORD = "your_db_password"  # Replace with your database password
DB_PORT = 3306  # Replace with your database port if it's not the default 3306


def connect_and_query():
    """Connects to the MySQL database, executes a SELECT query, and prints the results."""

    try:
        # Establish a connection to the database
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT  #  Include the port number
        )

        # Create a cursor object to execute SQL queries
        mycursor = mydb.cursor()

        # SQL query to select all rows from a table
        sql = "SELECT * FROM your_table_name"  # Replace with your actual table name

        # Execute the query
        mycursor.execute(sql)

        # Fetch all the results
        myresult = mycursor.fetchall()

        # Print the results
        for row in myresult:
            print(row)  # Prints each row as a tuple

            # Or, if you want to print each column separately:
            # print(f"Column1: {row[0]}, Column2: {row[1]}, Column3: {row[2]}") # Adjust indices as needed

    except mysql.connector.Error as err:
        print(f"Error: {err}")  # Print the error message if connection or query fails
    finally:
        # Close the cursor and the database connection
        if 'mycursor' in locals() and mycursor:  # check if cursor exists before closing
            mycursor.close()
        if 'mydb' in locals() and mydb:  # check if db exists before closing
            mydb.close()
        print("Connection closed.")  #Informative message


if __name__ == "__main__":
    connect_and_query()

