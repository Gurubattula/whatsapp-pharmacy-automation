from thefuzz import process

def find_best_match(user_input, db_medicine_names):
    if not db_medicine_names:
        return None
    # Extract the best match with a score
    match, score = process.extractOne(user_input, db_medicine_names)
    # 70 is a good threshold for medicine names
    return match if score > 70 else None