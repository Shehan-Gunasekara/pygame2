import sqlite3
import datetime

class DB_Helper:
    def __init__(self):
        self.db_connection = self.connect_db()
        self.start_time = None  

    def connect_db(self):
        """Connect to SQLite database."""
        return sqlite3.connect('user_data.db')

    def init_game_session(self):
        """
        
        Initialize a new game session.

        """
        self.start_time = datetime.datetime.utcnow()
        print("Game session started at:", self.start_time)

    def update_session_count(self):
        """
        Increment session count in the database.
        
        """
        conn = self.connect_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE game_stats
            SET total_sessions = total_sessions + 1
            WHERE user_id = 1
        ''')
        
        conn.commit()
        conn.close()
        print("Session count updated.")

    def update_total_played_time(self):
        """
        Update total played time by calculating elapsed minutes.
        
        """
        if not self.start_time:
            print("Error: Game session has not been initialized!")
            return
        
        end_time = datetime.datetime.utcnow()
        played_minutes = int((end_time - self.start_time).total_seconds() / 60) 

        conn = self.connect_db()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE game_stats
            SET total_minutes = total_minutes + ?
            WHERE user_id = 1
        ''', (played_minutes,))

        conn.commit()
        conn.close()
        print(f"Total played time updated: {played_minutes} minutes.")

    def update_achievements(self, achievements_earned):
        """
        Update total achievements in the database.

        Pass no. of achievements every time user achive something
        
        """
        conn = self.connect_db()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE game_stats
            SET total_achievements = total_achievements + ?
            WHERE user_id = 1
        ''', (achievements_earned,))

        conn.commit()
        conn.close()
        print(f"Achievements updated by {achievements_earned}.")


    def get_user_data(self, user_id=1):
        """Fetch user details from the database."""
        conn = self.connect_db()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()

        conn.close()
        if user_data:
            return {
                "id": user_data[0],
                "age": user_data[1],
                "location": user_data[2],
                "gender": user_data[3],
                "difficulty": user_data[4]
            }
        else:
            print(f"No user found with ID {user_id}")
            return None

    def get_game_data(self, user_id=1):
        """Fetch game statistics for a user."""
        conn = self.connect_db()
        cursor = conn.cursor()

        cursor.execute('SELECT total_sessions, total_minutes, total_achievements FROM game_stats WHERE user_id = ?', (user_id,))
        game_data = cursor.fetchone()

        conn.close()
        if game_data:
            return {
                "total_sessions": game_data[0],
                "total_minutes": game_data[1],
                "total_achievements": game_data[2]
            }
        else:
            print(f"No game data found for user ID {user_id}")
            return None

    def end_game_session(self):
        """
        
        Ends the game session and updates session details.
        
        """
        self.update_total_played_time()
        self.update_session_count()
        print("Game session ended.")
