# Credit to @sumanadhikari
# https://medium.com/@sumanadhikari/building-a-movie-recommendation-engine-using-scikit-learn-8dbb11c5aa4b
#
# HOW TO RUN IN TERMINAL
# python3 --version
# pip --version (ensure they exist)
#
# python3 -m venv sklearn-env
# source sklearn-env/bin/activate (activates virtual environment)
# (make sure scikit learn is installed https://scikit-learn.org/stable/install.html)
# (make sure pandas is installed https://pandas.pydata.org/pandas-docs/stable/getting_started/install.html)
#
# python ai.py
# Uncomment printing to see results


import random
import pandas as p
import csv
import numpy as n
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
from django.conf import settings

# Required for django
syrup_file_path = os.path.join(settings.BASE_DIR, 'backend/Syrups.csv')
soda_file_path = os.path.join(settings.BASE_DIR, 'backend/Sodas.csv')

# CSV related functions
def get_name_from_index(file, index):
    return file[file.index == index]["name"].values[0]

def get_index_from_name(file, name):
    return file[file.name == name]["index"].values[0]


# Return a list of syrups most similar to user_preference
def generate_similar_syrup_preferences(user_preference):
    syrups = p.read_csv(syrup_file_path)

    cv = CountVectorizer()
    count_matrix = cv.fit_transform(syrups["type"])
    similarity = cosine_similarity(count_matrix)

    user_pref_index = get_index_from_name(syrups, user_preference)
    similar_preferences =  list(enumerate(similarity[user_pref_index]))
    sorted_similar_pref = sorted(similar_preferences,key=lambda x:x[1],reverse=True)

    # Printing Test
    # print("--- Syrup flavors similar to " + user_preference + " ---")
    i = 0
    top5_preferences = []
    for item in sorted_similar_pref:
        # print(get_name_from_index(syrups, item[0]))
        top5_preferences.append(get_name_from_index(syrups, item[0]))
        i += 1
        if i == 5:
            break

    # print()
    return top5_preferences


# Generate best soda option based on chosen syrup flavors
def generate_best_soda(syrups, prefs):
    sodas = p.read_csv(soda_file_path)
    syrupList = p.read_csv(syrup_file_path)

    def get_type_from_name(name):
        return syrupList[syrupList.name == name]["type"].values[0]

    # Get types of each syrup and add to syrupTypes (only one entry per type)
    syrupTypes = []
    for syrup in syrups:
        syrupType = get_type_from_name(syrup)
        syrupType = syrupType.split()
        for item in syrupType:
            if item not in syrupTypes:
                syrupTypes.append(item)

    syrupTypes = " ".join(syrupTypes)

    # Credit: chatgpt
    # Add a new row to the csv file -- need to do this since the AI can only compare things within the same file
    with open(soda_file_path, mode='r', newline='') as file:
        reader = csv.reader(file)
        rows = list(reader)  # Read all existing rows into a list
        file.close()

    # Array that we want to add as a new row
    new_row = [len(rows) - 2, 'syrupTypes', 'n/a', 'n/a', syrupTypes]

    rows.append(new_row)

    # Write all rows back to the file, including the new row
    with open(soda_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows)  # Write all rows back to the file
        file.close()
    # end of chatgpt section

    sodas = p.read_csv(soda_file_path) # Reread now that new row is added
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(sodas["best-match-flavors"])
    similarity = cosine_similarity(count_matrix)

    best_sodas =  list(enumerate(similarity[len(rows) - 2]))
    sorted_best_sodas = sorted(best_sodas,key=lambda x:x[1],reverse=True)[1:]

    # Credit: chatgpt
    # Remove row we added to csv file, this way the sodas file wont get infinitely huge
    with open(soda_file_path, mode='r', newline='') as file:
        reader = csv.reader(file)
        rows = list(reader)
        file.close()

    # Remove the specified row
    if 0 <= len(rows) - 1 < len(rows):
        rows.pop(len(rows) - 1)  # Remove the row at the specified index

    with open(soda_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows)
        file.close()
    # end of chatgpt section

    def get_calorie_from_index(index):
        return sodas[sodas.index == index]["calorie"].values[0]

    # Printing Test
    # print("--- Best Match Sodas ---")
    i = 0
    top5_sodas = []
    # If user had no soda preferences, pick a random one from the top 5 sodas that best match the syrup flavors
    if len(prefs) == 0:
        for item in sorted_best_sodas:
            # print(get_name_from_index(sodas, item[0]))
            top5_sodas.append(get_name_from_index(sodas, item[0]))
            
            i += 1
            if i == 5:
                break
        # print()
        return top5_sodas[random.randint(0, len(top5_sodas) - 1)]

    # If user had multiple soda preferences, pick the preference that best matches the syrup flavors
    else:
        for item in sorted_best_sodas:
            if get_name_from_index(sodas, item[0]) in prefs:
                return get_name_from_index(sodas, item[0])


# TODO: Generate best add-in options based on chosen syrup flavors (maybe pick 0-2?)



# Credit: chatgpt
# Create list of all entries in the "name" column (column 2) of a csv file
def create_list(csv_file_name):
    names = []
    with open(csv_file_name, mode='r', newline='') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row
        for row in reader:
            names.append(row[1])  # Assuming 'name' is in the second column (index 1)

        file.close()
    return names

# MAIN FUNCTION
# user_preferences is either
# a) list of the user's preferences
# b) list of (syrup) flavors, sodas, and add-ins from popular / highly rated drinks
def generate_soda(user_preferences):
    drink = {}
    validSyrups = create_list(syrup_file_path)
    validSodas = create_list(soda_file_path)

    syrupPrefs = []
    sodaPrefs = []
    for item in user_preferences:
        if item.lower() in validSyrups:
            syrupPrefs.append(item.lower())
        elif item.lower() in validSodas:
            sodaPrefs.append(item.lower())

    if len(syrupPrefs) == 0: # if user has no syrup prefs we can send the popular flavors instead
        return drink # empty
    else:
        # Randomly picking 1-2 of the syrup preferences to create a drink with
        chosenSyrupPrefs = []
        rand_pref_1 = random.randint(0, len(syrupPrefs) - 1)
        rand_pref_2 = random.randint(0, len(syrupPrefs) - 1)
        chosenSyrupPrefs.append(syrupPrefs[rand_pref_1])
        if not rand_pref_1 == rand_pref_2:
            chosenSyrupPrefs.append(syrupPrefs[rand_pref_2])

        syrupsToUse = []
        # Send chosen preferences to Syrup AI
        for pref in chosenSyrupPrefs:
            top5 = generate_similar_syrup_preferences(pref)

            # Can have duplicate syrups the way this is coded right now
            # Pick 1-2 random flavors from the top 5
            rand_top5_1 = random.randint(0, len(top5) - 1)
            rand_top5_2 = random.randint(0, len(top5) - 1)
            syrupsToUse.append(top5[rand_top5_1])
            syrupsToUse.append(top5[rand_top5_2])

        # Printing Test
        # print("Generated Syrups:")
        # for syrup in syrupsToUse:
        #     print(syrup)
        # print()
        drink["syrups"] = syrupsToUse

        # Pick a preffered soda that best matches the generated syrups
        # Auto pick soda if there is only 1 soda in preferences
        if len(sodaPrefs) == 1:
            drink["soda"] = [sodaPrefs[0]]
        else:
            drink["soda"] = [generate_best_soda(syrupsToUse, sodaPrefs)]

        # TODO: Pick a preffered add-in that best matches the generated syrups

        # TODO: add list of add-ins to drink (list length = empty, 1, or 2)
        return drink


# Filler, generate_soda() would get called elsewhere. Feel free to mess around with the list
# user_preferences = ["mango", "watermelon", "vanilla", "sour", "peach", "strawberry", "lavender"]
# print(generate_soda(user_preferences))