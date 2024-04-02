from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from datetime import datetime
from fractions import Fraction
import sqlite3, requests, os, inflect, csv


options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(service=ChromeService(executable_path=ChromeDriverManager().install()), options=options)
p = inflect.engine()

db_file = r"../accessRecipe2/db.sqlite3"

cooking_units = [
    {"singular": "teaspoon", "short": "tsp", "plural": "teaspoons", "short_plural": "tsps"},
    {"singular": "tablespoon", "short": "tbsp", "plural": "tablespoons", "short_plural": "tbsps"},
    {"singular": "fluid ounce", "short": "fl oz", "plural": "fluid ounces", "short_plural": "fl ozs"},
    {"singular": "cup", "short": "c", "plural": "cups", "short_plural": "cs"},
    {"singular": "pint", "short": "pt", "plural": "pints", "short_plural": "pts"},
    {"singular": "quart", "short": "qt", "plural": "quarts", "short_plural": "qts"},
    {"singular": "gallon", "short": "gal", "plural": "gallons", "short_plural": "gals"},
    {"singular": "ounce", "short": "oz", "plural": "ounces", "short_plural": "ozs"},
    {"singular": "pound", "short": "lb", "plural": "pounds", "short_plural": "lbs"},
]

def convert_to_metric(quantity, unit):
    conversion_factors = {
        "tsp": {"factor": 5, "metric_unit": "ml"},
        "teaspoon": {"factor": 5, "metric_unit": "ml"},
        "tbsp": {"factor": 15, "metric_unit": "ml"},
        "tablespoon": {"factor": 15, "metric_unit": "ml"},
        "tablespoons": {"factor": 15, "metric_unit": "ml"},
        "fl oz": {"factor": 30, "metric_unit": "ml"},
        "cup": {"factor": 240, "metric_unit": "ml"},
        "cups": {"factor": 240, "metric_unit": "ml"},
        "pt": {"factor": 0.47, "metric_unit": "l"},
        "qt": {"factor": 0.95, "metric_unit": "l"},
        "quart": {"factor": 0.95, "metric_unit": "L"},
        "quarts": {"factor": 0.95, "metric_unit": "L"},
        "gal": {"factor": 3.8, "metric_unit": "l"},
        "gallon": {"factor": 3.8, "metric_unit": "l"},
        "gallons": {"factor": 3.8, "metric_unit": "l"},
        "oz": {"factor": 28, "metric_unit": "g"},
        "ounce": {"factor": 28, "metric_unit": "g"},
        "lb": {"factor": 0.45, "metric_unit": "kg"},
        "pounds": {"factor": 0.45, "metric_unit": "kg"},
        "pound": {"factor": 0.45, "metric_unit": "kg"},
        "pint": {"factor": 0.473176, "metric_unit": "L"},
        "pints": {"factor": 0.473176, "metric_unit": "L"},
        "": {"factor": 0, "metric_unit": ""}
    }

    if unit in conversion_factors:
        metric_quantity = quantity * conversion_factors[unit]["factor"]
        metric_unit = conversion_factors[unit]["metric_unit"]
        return metric_quantity, metric_unit
    else:
        return None
    
def convert_to_short_form(long_form):
    short_forms = {
        "teaspoon": "tsp",
        "tablespoon": "tbsp",
        "fluid ounce": "fl_oz",
        "cup": "cup",
        "pint": "pt",
        "quart": "qt",
        "gallon": "gal",
        "ounce": "oz",
        "pound": "lb",
    }

    return short_forms.get(long_form, long_form)

def is_item_in_units(item, units):
    for unit in units:
        if item in unit.values():
            return True
    return False

try:

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    print("Connected to " + db_file)

    driver.get('https://publicdomainrecipes.org/')

    driver.implicitly_wait(20)

    for x in range(1, 121): 
        
        print("Page: " + str(x))

        flexItems = driver.find_elements(By.CLASS_NAME, 'flex-item')

        numberofItems = len(flexItems)

        for i in range(numberofItems):

            flexItems[i].find_element(By.TAG_NAME, 'a').click()

            driver.implicitly_wait(20)

            recipeName = driver.find_element(By.TAG_NAME, 'h1').text
            print(recipeName)

            cursor.execute('SELECT * FROM recipes_recipes WHERE "title" = ?', (recipeName,))

            recipe = cursor.fetchone()

            if recipe is None:
                
                file_path = f'../accessRecipe2/media/recipe/images/{recipeName}.jpg'

                if not os.path.isfile(file_path):

                    img = driver.find_element(By.TAG_NAME, 'figure').find_element(By.TAG_NAME, 'img')
                    img_url = img.get_attribute('src')
                    response = requests.get(img_url)

                    with open(file_path, 'wb') as f:
                        f.write(response.content)

                else:
                    print("Image already exists")

                query = 'SELECT * FROM recipes_images WHERE "image" = ?'
                values = (f'recipe/images/{recipeName}.jpg',)
                cursor.execute(query, values)
                dbCheck = cursor.fetchone()

                if dbCheck is None:
                    query = 'INSERT INTO recipes_images ("image", "created_at", "updated_at", created_by_id, last_modified_by_id) VALUES (?,?,?,?,?)'
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    values = (f'recipe/images/{recipeName}.jpg', current_time, current_time, 1, 1)
                    cursor.execute(query, values)  

                    imageID = cursor.lastrowid

                else:
                    imageID = dbCheck[0]

                print("image ID = " + str(imageID))
                
                ingredientArr = []

                print("Other Information: ")
                OtherInfo = driver.find_element(By.CLASS_NAME, 'taxo-display').find_elements(By.TAG_NAME, 'p')
                source = ""
                for info in OtherInfo:
                    print("\t" + info.text)
                    if info.text.startswith("Ingredient"):
                        ingredients = info.text.split(': ')[1].split(', ')
                        for ingredient in ingredients:
                            if ingredient == "":
                                
                                with open('./missingIngredient.csv.', 'a', newline='') as csvfile:
                                    writer = csv.writer(csvfile)
                                    writer.writerow([recipeName + " " + str(x)])
                                continue

                            cursor.execute('SELECT * FROM recipes_ingredients WHERE "name" = ? OR "name" = ? OR "plural_name" = ? OR "plural_name" = ?', (ingredient.capitalize(), ingredient, ingredient.capitalize(), ingredient))
                            ingredientDB = cursor.fetchone()

                            print(ingredient)
                            
                            if ingredientDB is None:
                                query = 'INSERT INTO recipes_ingredients ("name", "plural_name", "created_at", "updated_at", created_by_id, last_modified_by_id) VALUES (?,?,?,?,?,?)'
                                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                values = (ingredient.capitalize(), p.plural(ingredient.capitalize()), current_time, current_time, 1, 1)
                                cursor.execute(query, values)
                                ingredientArr.append([ingredient, p.plural(ingredient), cursor.lastrowid])

                                # cursor.execute('SELECT * FROM profiles_profiles_my_ingredients WHERE "profile_id" = ? and ingredients_id = ?', (1, cursor.lastrowid))
                                # my_ingredient = cursor.fetchone()

                                # if my_ingredient is None:
                                #     query = 'INSERT INTO profiles_profiles_my_ingredients ("profiles_id", "ingredients_id") VALUES (?,?)'
                                #     values = (1, cursor.lastrowid)
                                #     cursor.execute(query, values)

                            else:
                                ingredientArr.append([ingredient, p.plural(ingredient), ingredientDB[0]])

                    elif info.text.startswith("Category:"):
                        categories = info.text.split(': ')[1].split(', ')
                        categoriesArr = []
                        for category in categories:
                            query = 'SELECT * FROM recipes_categories WHERE "name" = ?'
                            values = (category,)
                            cursor.execute(query, values)
                            dbCheck = cursor.fetchone()

                            if dbCheck is None:
                                query = 'INSERT INTO recipes_categories ("name", "created_at", "updated_at", created_by_id, last_modified_by_id) VALUES (?,?,?,?,?)'
                                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                values = (category, current_time, current_time, 1, 1)
                                cursor.execute(query, values)

                                categoriesArr.append(cursor.lastrowid)
                            else:
                                categoriesArr.append(dbCheck[0])
                    elif info.text.startswith("Source:"):
                        source = info.text.split(': ')[1]
                    

                print("Ingredients: ")
                print(ingredientArr)

                assignedIngredientsArr = []
                assignedIngredients = driver.find_elements(By.TAG_NAME, 'ul')[2].find_elements(By.TAG_NAME, 'li')
                for assignedIngredient in assignedIngredients:
                    print("\t" + assignedIngredient.text)
                    number = 0.00
                    decimal = 0.00
                    imp_unit = ""
                    metric_unit = ""
                    for ingredient in ingredientArr:
                        assginedIngredientTextArr = assignedIngredient.text.split(' ')
                        if ingredient[0] in assginedIngredientTextArr or ingredient[1] in assginedIngredientTextArr:
                            for item in assginedIngredientTextArr:
                                if item.isdigit():
                                    number = float(item)
                                elif '/' in item and item.split('/')[0].isdigit() and item.split('/')[1].isdigit():
                                    try:
                                        decimal = float(Fraction(item))
                                    except:
                                        decimal = number / float(item.split('/')[1])
                                        number = 0.00

                                if is_item_in_units(item, cooking_units):
                                    imp_unit = item
                    
                    
                            number = round(number + decimal, 2)
                            print(str(number) + " " + imp_unit)

                            query = 'SELECT * FROM recipes_assigned_ingredients WHERE "imperial_amount" = ? and "imperial_units" = ? and "ingredient_id" = ?'
                            values = (number, imp_unit, ingredient[2])
                            cursor.execute(query, values)
                            dbCheck = cursor.fetchone()
                            
                            if dbCheck is None:
                                query = 'INSERT INTO recipes_assigned_ingredients ("metric_amount", "imperial_amount", "metric_units", "imperial_units", "ingredient_id", "created_at", "updated_at", created_by_id, last_modified_by_id) VALUES (?,?,?,?,?,?,?,?,?)'
                                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                metric_amount, metric_unit = convert_to_metric(number, imp_unit)
                                short_imp_form = convert_to_short_form(imp_unit)
                                values = (metric_amount, number, metric_unit, short_imp_form, ingredient[2], current_time, current_time, 1, 1)
                                cursor.execute(query, values)
                                assignedIngredientsArr.append(cursor.lastrowid)
                            else:
                                assignedIngredientsArr.append(dbCheck[0])

                            
                                
                directionsArr = []             
                print("Directions: ")
                directions = driver.find_element(By.TAG_NAME, 'ol').find_elements(By.TAG_NAME, 'li')
                for direction in directions:
                    print("\t" + direction.text)
                    directionTextArr = direction.text.split('.')[0].split(' ')

                    ingredientsToAddArr = []
                    for directionText in directionTextArr:
                        for ingredient in ingredientArr:
                            if directionText.lower() == ingredient[0] or directionText.lower() == ingredient[1]:
                                query = 'SELECT * FROM recipes_ingredients WHERE name = ? OR plural_name = ?'
                                values = (ingredient[0].capitalize(), ingredient[1].capitalize())
                                cursor.execute(query, values)
                                ingredientDB = cursor.fetchone()

                                if ingredientDB is not None:
                                    ingredientsToAddArr.append(ingredientDB[0])
                        
                    if direction.text != ".":

                        query = 'INSERT INTO recipes_instructions ("description", "created_at", "updated_at", created_by_id, last_modified_by_id) VALUES (?,?,?,?,?)'
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        values = (direction.text, current_time, current_time, 1, 1)
                        cursor.execute(query, values)
                        directionID = cursor.lastrowid
                        directionsArr.append(directionID)
            

                    for ingredientID in ingredientsToAddArr:
                        query = 'SELECT * FROM recipes_instructions_ingredients WHERE "instructions_id" = ? and "ingredients_id" = ?'
                        values = (directionID, ingredientID)
                        cursor.execute(query, values)
                        dbCheck = cursor.fetchone()

                        if dbCheck is None:
                            query = 'INSERT INTO recipes_instructions_ingredients ("instructions_id", "ingredients_id") VALUES (?,?)'
                            values = (directionID, ingredientID)
                            print(str(directionID) + " " +  str(ingredientID))
                            cursor.execute(query, values)
                            

                parahraphs = driver.find_elements(By.TAG_NAME, 'p')
                serving = 0
                for paragraph in parahraphs:
                    if paragraph.text.startswith("Yield:"):
                        servings = paragraph.text.split(': ')[1].split(' ')[0]
                        print("Servings: " + servings)
                        break
                
                # for direction in directionsArr:
                #     query = 'SELECT * FROM profiles_profiles_my_instructions WHERE "profiles_id" = ? and "instructions_id" = ?'
                #     values = (1, direction)
                #     cursor.execute(query, values)
                #     dbCheck = cursor.fetchone()

                #     if dbCheck is None:
                #         query = 'INSERT INTO profiles_profiles_my_instructions ("profiles_id", "instructions_id") VALUES (?,?)'
                #         values = (1, direction)
                #         cursor.execute(query, values)

                query = 'SELECT * FROM recipes_recipes WHERE "title" = ? AND created_by_id = ?'
                values = (recipeName, 1)
                cursor.execute(query, values)
                dbCheck = cursor.fetchone()
                
                if dbCheck is None:
                    query = 'INSERT INTO recipes_recipes ("title", "measurement_type", "description", "servings", "created_at", "updated_at", created_by_id, last_modified_by_id, "publish", "suspended", "source", main_image_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)'
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    values = (recipeName, 'imperial', '', serving, current_time, current_time, 1, 1, 1, 0, source, imageID)
                    cursor.execute(query, values)
                    recipeID = cursor.lastrowid

                else:
                    recipeID = dbCheck[0]

                for category in categoriesArr:
                    query = 'SELECT * FROM recipes_recipes_categories WHERE "recipes_id" = ? and "categories_id" = ?'
                    values = (recipeID, category)
                    cursor.execute(query, values)
                    dbCheck = cursor.fetchone()

                    if dbCheck is None:
                        query = 'INSERT INTO recipes_recipes_categories ("recipes_id", "categories_id") VALUES (?,?)'
                        values = (recipeID, category)
                        cursor.execute(query, values)

                for assignedIngredient in assignedIngredientsArr:
                    query = 'SELECT * FROM recipes_recipes_ingredients WHERE "recipes_id" = ? and "assigned_ingredients_id" = ?'
                    values = (recipeID, assignedIngredient)
                    cursor.execute(query, values)
                    dbCheck = cursor.fetchone()

                    if dbCheck is None:
                        query = 'INSERT INTO recipes_recipes_ingredients ("recipes_id", "assigned_ingredients_id") VALUES (?,?)'
                        values = (recipeID, assignedIngredient)
                        cursor.execute(query, values)

                for direction in directionsArr:
                    query = 'SELECT * FROM recipes_recipes_instructions WHERE "recipes_id" = ? and "instructions_id" = ?'
                    values = (recipeID, direction)
                    cursor.execute(query, values)
                    dbCheck = cursor.fetchone()

                    if dbCheck is None:
                        query = 'INSERT INTO recipes_recipes_instructions ("recipes_id", "instructions_id") VALUES (?,?)'
                        values = (recipeID, direction)
                        cursor.execute(query, values)

            driver.implicitly_wait(20)

            driver.back()

            flexItems = driver.find_elements(By.CLASS_NAME, 'flex-item')

            conn.commit()

        

        driver.get('https://publicdomainrecipes.org/page/' + str(x + 1) + '/')

        driver.implicitly_wait(20)
        
        
    conn.close() 
except Exception as e:
    print("Error:", e)