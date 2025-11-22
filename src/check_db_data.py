import sqlite3

DB_NAME = 'pmda.sqlite'

def check_medicine_data():
    """
    medicinesテーブルの全データを取得して表示します。
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT * FROM medicines")
    medicines = cur.fetchall()

    if medicines:
        print("\n--- medicines テーブルのデータ ---")
        # カラム名を取得
        column_names = [description[0] for description in cur.description]
        print(column_names)
        for medicine in medicines:
            print(medicine)
    else:
        print("\n--- medicines テーブルにデータはありません ---")
    
    conn.close()

def check_interaction_data():
    """
    interactionsテーブルの全データを取得して表示します。
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT * FROM interactions")
    interactions = cur.fetchall()

    if interactions:
        print("\n--- interactions テーブルのデータ ---")
        # カラム名を取得
        column_names = [description[0] for description in cur.description]
        print(column_names)
        for interaction in interactions:
            print(interaction)
    else:
        print("\n--- interactions テーブルにデータはありません ---")
    
    conn.close()

if __name__ == '__main__':
    check_medicine_data()
    check_interaction_data()
