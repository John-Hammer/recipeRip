import sqlite3

db_file = r"../accessRecipe2/db.sqlite3"
try:

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print("Connected to " + db_file)

    cursor.execute('SELECT * FROM recipes_recipes WHERE servings = 1')
    recipes = cursor.fetchall()

    for recipe in recipes:
        print(recipe)
        cursor.execute('UPDATE recipes_recipes SET servings = 0 WHERE id = ?', (recipe[0],))
    conn.commit()
    

    conn.close() 
except Exception as e:
    print("Error:", e)