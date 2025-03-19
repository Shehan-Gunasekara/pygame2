import eel
import os
import sqlite3

eel.init('web')

def close_app():
    os._exit(0)

eel.expose(close_app)


def connect_db():
    return sqlite3.connect('user_data.db')

def create_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            age INTEGER,
            location TEXT,
            gender TEXT,
            difficulty TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total_sessions INTEGER DEFAULT 0,
            total_minutes INTEGER DEFAULT 0,
            total_achievements INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
            )
    ''')
    conn.commit()
    conn.close()

def insert_or_update_user(age, location, gender, difficulty):
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = 1')
    user = cursor.fetchone()

    if user:
        cursor.execute('''
            UPDATE users
            SET age = ?, location = ?, gender = ?, difficulty = ?
            WHERE id = 1
        ''', (age, location, gender))
    else:
        cursor.execute('''
            INSERT INTO users (age, location, gender, difficulty)
            VALUES (?, ?, ?, ?)
        ''', (age, location, gender, difficulty))

        cursor.execute('''
            INSERT INTO game_stats (
                user_id,
                total_sessions,
                total_minutes,
                total_achievements
                )
            VALUES (?, ?, ?, ?)
        ''', (1, 0, 0, 0))
    
    
    conn.commit()
    conn.close()

def get_user_data():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = 1')
    user = cursor.fetchone()
    conn.close()
    return user

@eel.expose
def get_user():
    user = get_user_data()
    print(user)
    if user:
        return {'age': user[1], 'location': user[2], 'gender': user[3], 'difficulty': user[4]}
    else:
        return None


@eel.expose
def submit_form(age, location, gender, difficulty):
    print(f"Submitted: Age={age}, Location={location}, Gender={gender}, difficulty={difficulty}")
    insert_or_update_user(age, location, gender, difficulty)
    os.system("python game.py") 


@eel.expose
def open_game():
    os.system("python game.py")  
    os._exit(0)



create_db()


eel.start('templates/index.html', size=(800, 600), )
