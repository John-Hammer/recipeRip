from urllib.parse import urlparse
from dotenv import load_dotenv
import sqlite3
import psycopg2
import os

load_dotenv()

db_file = r"../GitHub/accessRecipe2/db.sqlite3"

try:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    print("Connected to SQLite database:", db_file)

    url = urlparse(os.environ.get('DATABASE_URL', ''))
    dbname = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port

    try:
        conn2 = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        cursor2 = conn2.cursor()
        print("Connected to PostgreSQL database:", os.environ.get('DATABASE_URL', ''))

        tables = [
            # 'recipes_images',
            # 'recipes_categories',
            # 'recipes_ingredients',
            # 'recipes_assigned_ingredients',
            'recipes_instructions',
            'recipes_instructions_ingredients',
            'recipes_recipes',
            'recipes_recipes_ingredients',
            'recipes_recipes_instructions',
            'recipes_recipes_categories',
        ]

        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            data = cursor.fetchall()
            
            for row in data:
                modified_row = [float(value) if isinstance(value, str) and value.replace('.', '', 1).isdigit() else value for value in row]
                # print(modified_row)
                if table == "recipes_instructions" and modified_row[4] is None:
                    modified_row[4] = 0  # Replace with your default value
                
                if table != "recipes_assigned_ingredients":
                    cursor2.execute(f"INSERT INTO {table} VALUES ({', '.join(['%s'] * len(modified_row))})", modified_row)
                elif table == "recipes_instructions":
                    query = f'''INSERT INTO {table} (id, description, created_at, updated_at, image_id, created_by_id, last_modified_by_id, "order") VALUES ({', '.join(['%s'] * len(modified_row))})'''
                    cursor2.execute(query, tuple(modified_row))
                else:
                    query = f'''INSERT INTO {table} (id, imperial_amount, metric_units, imperial_units, created_at, updated_at, "order", created_by_id, last_modified_by_id, ingredient_id, metric_amount) VALUES ({', '.join(['%s'] * len(modified_row))})'''
                    cursor2.execute(query, tuple(modified_row))

            conn2.commit()
            print(table + " imported successfully.")

    except Exception as e:
        print("Error connecting to PostgreSQL:", e)

    finally:
        conn2.close()

except Exception as e:
    print("Error connecting to SQLite:", e)

finally:
    conn.close()
