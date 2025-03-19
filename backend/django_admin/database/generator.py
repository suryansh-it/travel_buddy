# filepath: /Users/anujjainbatu/Desktop/travel-buddy/database/generator_script.py
import psycopg2

# Database connection parameters
conn = psycopg2.connect(
    dbname="travel_buddy_db",
    user="travel_bud",  # Replace with your PostgreSQL username
    password="suryansh",  # Replace with your PostgreSQL password
    host="localhost"
)
# -----to create----
# cur = conn.cursor()

# # SQL statements to create tables
# create_tables = [
#     """
#     CREATE TABLE countries (
#         id SERIAL PRIMARY KEY,
#         name VARCHAR(100) UNIQUE NOT NULL,
#         code VARCHAR(10) UNIQUE NOT NULL
#     );
#     """,
#     """
#     CREATE TABLE categories (
#         id SERIAL PRIMARY KEY,
#         name VARCHAR(100) UNIQUE NOT NULL
#     );
#     """,
#     """
#     CREATE TABLE apps (
#         id SERIAL PRIMARY KEY,
#         name VARCHAR(255) NOT NULL,
#         description TEXT,
#         category_id INT REFERENCES categories(id) ON DELETE CASCADE,
#         google_play_link TEXT,
#         apple_store_link TEXT,
#         apk_link TEXT,
#         rating DECIMAL(2,1),
#         total_downloads BIGINT,
#         verified BOOLEAN DEFAULT FALSE,
#         languages_supported JSONB,
#         offline_support BOOLEAN DEFAULT FALSE,
#         free_or_paid VARCHAR(20) CHECK (free_or_paid IN ('Free', 'Freemium', 'Paid')),
#         features JSONB,
#         requires_registration BOOLEAN DEFAULT FALSE
#     );
#     """,
#     """
#     CREATE TABLE country_app_mapping (
#         id SERIAL PRIMARY KEY,
#         country_id INT REFERENCES countries(id) ON DELETE CASCADE,
#         app_id INT REFERENCES apps(id) ON DELETE CASCADE
#     );
#     """,
#     """
#     CREATE TABLE app_screenshots (
#         id SERIAL PRIMARY KEY,
#         app_id INT REFERENCES apps(id) ON DELETE CASCADE,
#         image_url TEXT NOT NULL
#     );
#     """,
#     """
#     CREATE TABLE reviews (
#         id SERIAL PRIMARY KEY,
#         app_id INT REFERENCES apps(id) ON DELETE CASCADE,
#         user_id UUID NOT NULL,
#         rating DECIMAL(2,1) CHECK (rating BETWEEN 1 AND 5),
#         review_text TEXT,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#     );
#     """
# ]

# # Execute each SQL statement
# for create_table in create_tables:
#     cur.execute(create_table)

# # Commit the changes and close the connection
# conn.commit()
# cur.close()
# conn.close()

# print("Tables created successfully.")

# ----to DELETE-----
# cur = conn.cursor()

# # Drop tables in reverse order to avoid dependency issues
# drop_tables = [
#     "DROP TABLE IF EXISTS reviews CASCADE;",
#     "DROP TABLE IF EXISTS app_screenshots CASCADE;",
#     "DROP TABLE IF EXISTS country_app_mapping CASCADE;",
#     "DROP TABLE IF EXISTS apps CASCADE;",
#     "DROP TABLE IF EXISTS categories CASCADE;",
#     "DROP TABLE IF EXISTS countries CASCADE;"
# ]

# for drop_table in drop_tables:
#     cur.execute(drop_table)

# # Commit and close connection
# conn.commit()
# cur.close()
# conn.close()

# print("Tables deleted successfully.")