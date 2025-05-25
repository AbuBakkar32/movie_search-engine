# locustfile.py
import random
from locust import HttpUser, task, between, events
import os # For checking file existence

# --- Configuration ---
# Path to your query file generated in Step 2
QUERY_FILE_PATH = "queries.txt"
# Path to a file containing sample tconst IDs (one per line)
# You'll need to create this file. Example content:
# tt0111161
# tt0068646
# tt0133093
TCONST_FILE_PATH = "sample_tconsts.txt"

# Endpoints of your Django application
SEARCH_ENDPOINT = "/movies/search/"
MOVIE_DETAIL_ENDPOINT_TEMPLATE = "/movies/movie/{tconst}/" # Placeholder for tconst

@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--query-file", type=str, env_var="LOCUST_QUERY_FILE", default=QUERY_FILE_PATH, help="Path to the query file")
    parser.add_argument("--tconst-file", type=str, env_var="LOCUST_TCONST_FILE", default=TCONST_FILE_PATH, help="Path to the tconst sample file")


class IMDbUser(HttpUser):
    """
    Simulates a user interacting with the IMDb application.
    """
    # Users will wait between 1 and 3 seconds between tasks
    wait_time = between(1, 3)

    search_queries = []
    sample_tconsts = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_file_path = self.environment.parsed_options.query_file
        self.tconst_file_path = self.environment.parsed_options.tconst_file


    def on_start(self):
        """
        Called when a Locust user starts.
        Loads search queries and sample tconst IDs from their respective files.
        """
        # Load search queries
        try:
            if not os.path.exists(self.query_file_path):
                print(f"ERROR: Query file not found: {self.query_file_path}. Please ensure it exists or specify with --query-file.")
            else:
                with open(self.query_file_path, 'r', encoding='utf-8') as f:
                    self.search_queries = [line.strip() for line in f if line.strip()]
                if not self.search_queries:
                    print(f"WARNING: No queries loaded from {self.query_file_path}. The file might be empty.")
                else:
                    print(f"Successfully loaded {len(self.search_queries)} search queries from {self.query_file_path}.")
        except Exception as e:
            print(f"ERROR: An error occurred while reading {self.query_file_path}: {e}")

        # Load sample tconsts
        try:
            if not os.path.exists(self.tconst_file_path):
                print(f"ERROR: tconst sample file not found: {self.tconst_file_path}. Please ensure it exists or specify with --tconst-file. Movie detail tasks will be skipped.")
            else:
                with open(self.tconst_file_path, 'r', encoding='utf-8') as f:
                    self.sample_tconsts = [line.strip() for line in f if line.strip()]
                if not self.sample_tconsts:
                    print(f"WARNING: No tconsts loaded from {self.tconst_file_path}. Movie detail tasks might be skipped if list remains empty.")
                else:
                    print(f"Successfully loaded {len(self.sample_tconsts)} sample tconsts from {self.tconst_file_path}.")
        except Exception as e:
            print(f"ERROR: An error occurred while reading {self.tconst_file_path}: {e}")

        if not self.search_queries and not self.sample_tconsts:
            print("ERROR: No data loaded for tasks. Locust users might not perform any actions.")


    @task(3) # This task is 3 times more likely to be chosen
    def search_movie(self):
        """
        Simulates a user searching for a movie.
        """
        if not self.search_queries:
            # print("Skipping search_movie task: no queries available.")
            return

        query = random.choice(self.search_queries)
        self.client.get(f"{SEARCH_ENDPOINT}?q={query}", name=f"{SEARCH_ENDPOINT} [query_driven]")

    @task(2) # This task is 2 times more likely to be chosen
    def view_movie_detail(self):
        """
        Simulates a user viewing the details of a movie.
        Picks a random tconst from the loaded sample_tconsts list.
        """
        if not self.sample_tconsts:
            # print("Skipping view_movie_detail task: no sample tconsts available.")
            return

        tconst = random.choice(self.sample_tconsts)
        detail_url = MOVIE_DETAIL_ENDPOINT_TEMPLATE.format(tconst=tconst)
        self.client.get(detail_url, name=MOVIE_DETAIL_ENDPOINT_TEMPLATE) # Group all detail page requests under one name

    @task(1) # This task is 1 time as likely to be chosen (least frequent)
    def visit_search_page_directly(self):
        """
        Simulates a user landing on the search page without a query.
        """
        self.client.get(SEARCH_ENDPOINT, name=f"{SEARCH_ENDPOINT} [direct_visit]")


# To run this:
# 1. Create `queries.txt` (as per Step 2).
# 2. Create `sample_tconsts.txt` with a few valid tconst IDs from your database, one per line.
#    For example:
#    tt0111161
#    tt0068646
#    tt0133093
#    tt0468569
# 3. Make sure your Django development server is running (e.g., python manage.py runserver)
# 4. Open your terminal in the directory containing this locustfile.py, queries.txt, and sample_tconsts.txt
# 5. Run Locust: locust -f locustfile.py --host=http://127.0.0.1:8000
#    (Replace http://127.0.0.1:8000 with your Django app's host and port if different)
#    You can also specify file paths:
#    locust -f locustfile.py --host=http://127.0.0.1:8000 --query-file=my_queries.txt --tconst-file=my_tconsts.txt
# 6. Open your web browser and go to http://localhost:8089 (Locust's web UI)
# # 7. Enter the number of users to simulate and the spawn rate, then start swarming.