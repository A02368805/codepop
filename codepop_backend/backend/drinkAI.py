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


import random
import pandas as p
import csv
import numpy as n
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# CSV related functions
def get_name_from_index(file, index):
    return file[file.index == index]["name"].values[0]

def get_index_from_name(file, name):
    return file[file.name == name]["index"].values[0]



# Return a list of syrups most similar to user_preference
def generate_similar_syrup_preferences(user_preference):
    syrups = p.read_csv("Syrups.csv")

    cv = CountVectorizer()
    count_matrix = cv.fit_transform(syrups["type"])
    similarity = cosine_similarity(count_matrix)

    user_pref_index = get_index_from_name(syrups, user_preference)
    similar_preferences =  list(enumerate(similarity[user_pref_index]))
    sorted_similar_pref = sorted(similar_preferences,key=lambda x:x[1],reverse=True)

    print("--- Syrup flavors similar to " + user_preference + " ---")
    i = 0
    top5_preferences = []
    for item in sorted_similar_pref:
        print(get_name_from_index(syrups, item[0]))
        top5_preferences.append(get_name_from_index(syrups, item[0]))
        i += 1
        if i == 5:
            break

    print()
    return top5_preferences



# Generate best soda option based on chosen syrup flavors (generates diet only if user has a diet preference)
def generate_best_soda(syrups, diet):
    sodas = p.read_csv("Sodas.csv")
    syrupList = p.read_csv("Syrups.csv")

    def get_type_from_name(name):
        return syrupList[syrupList.name == name]["type"].values[0]

    # Check types of each syrup and add to syrupTypes (only one entry per type)
    syrupTypes = []
    for syrup in syrups:
        syrupType = get_type_from_name(syrup)
        syrupType = syrupType.split()
        for item in syrupType:
            if item not in syrupTypes:
                syrupTypes.append(item)

    syrupTypes = " ".join(syrupTypes)

    # Credit: chatgpt
    # Add a new row to the csv file -- need to do this since the AI can only compare with things in the same file
    with open('Sodas.csv', mode='r', newline='') as file:
        reader = csv.reader(file)
        rows = list(reader)  # Read all existing rows into a list
        file.close()

    # Array that we want to add as a new row
    new_row = [len(rows) - 2, 'syrupTypes', 'n/a', 'n/a', syrupTypes]

    rows.append(new_row)

    # Write all rows back to the file, including the new row
    with open('Sodas.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows)  # Write all rows back to the file
        file.close()
    # end of chatgpt section

    sodas = p.read_csv("Sodas.csv")
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(sodas["best-match-flavors"])
    similarity = cosine_similarity(count_matrix)

    best_sodas =  list(enumerate(similarity[len(rows) - 2]))
    sorted_best_sodas = sorted(best_sodas,key=lambda x:x[1],reverse=True)[1:]

    # Credit: chatgpt
    # Remove row we added to csv file, this way the sodas file wont get infinitely huge
    with open('Sodas.csv', mode='r', newline='') as file:
        reader = csv.reader(file)
        rows = list(reader)
        file.close()

    # Remove the specified row
    if 0 <= len(rows) - 1 < len(rows):
        rows.pop(len(rows) - 1)  # Remove the row at the specified index

    with open('Sodas.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows)
        file.close()
    # end of chatgpt section

    def get_calorie_from_index(index):
        return sodas[sodas.index == index]["calorie"].values[0]

    print("--- Best Match Sodas ---")
    i = 0
    top5_sodas = []
    if diet == True:
        for item in sorted_best_sodas:
            if get_calorie_from_index(item[0]) == "diet":
                print(get_name_from_index(sodas, item[0]))
                top5_sodas.append(get_name_from_index(sodas, item[0]))
                i += 1
                if i == 5:
                    break
    else: 
        for item in sorted_best_sodas:
            print(get_name_from_index(sodas, item[0]))
            top5_sodas.append(get_name_from_index(sodas, item[0]))
            
            i += 1
            if i == 5:
                break
    print()
    return top5_sodas
    


# MAIN FUNCTION
# user_preferences is either
# a) list of the user's preferences
# b) list of (syrup) flavors from popular / highly rated drinks
def generate_soda(user_preferences):
    diet = False
    if "diet" in user_preferences: # diet must be lowercase for this to work
        user_preferences.remove("diet")
        diet = True
    
    print("In this test, diet is: ")
    print(diet)
    print()

    # Randomly picking 1-2 of the preferences to create a drink with
    chosen_preferences = []
    rand_pref_1 = random.randint(0, len(user_preferences) - 1)
    rand_pref_2 = random.randint(0, len(user_preferences) - 1)
    chosen_preferences.append(user_preferences[rand_pref_1])
    if not rand_pref_1 == rand_pref_2:
        chosen_preferences.append(user_preferences[rand_pref_2])

    syrups_to_use = []
    # Send chosen preferences to Syrup AI
    for pref in chosen_preferences:
        top5 = generate_similar_syrup_preferences(pref)

        # Can have duplicate syrups the way this is coded right now
        # Pick 1-2 random flavors from the top 5
        rand_top5_1 = random.randint(0, len(top5) - 1)
        rand_top5_2 = random.randint(0, len(top5) - 1)
        syrups_to_use.append(top5[rand_top5_1])
        syrups_to_use.append(top5[rand_top5_2])

    print("Generated Syrups:")
    for syrup in syrups_to_use:
        print(syrup)
    print()

    # Pick a soda that best matches the generated syrups
    top5_sodas = generate_best_soda(syrups_to_use, diet)
    rand_soda = random.randint(0, len(top5_sodas) - 1)
    soda_to_use = top5_sodas[rand_soda]

    print("Generated Soda:")
    print(soda_to_use)



# Filler, generate_soda() would get called elsewhere. Feel free to mess around with the list
user_preferences = ["Mango", "Watermelon", "Vanilla", "Sour", "Peach", "Strawberry", "Lavender", "diet"]
generate_soda(user_preferences)