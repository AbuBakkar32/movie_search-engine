import random
from django.core.management.base import BaseCommand, CommandError
from django.db.models import F, Sum
from movies.models import Movie, Rating # Assuming your app is named 'movies'
from pathlib import Path

# Define the output file path (project root)
# Assuming this command is in imdb_project/movies/management/commands/
# and manage.py is in imdb_project/
# So, BASE_DIR.parent should give the project root where manage.py is.
# However, Django's BaseCommand typically runs from the directory of manage.py
# So, a relative path 'queries.txt' should place it next to manage.py
OUTPUT_FILE = 'queries.txt'
NUM_QUERIES = 10000

class Command(BaseCommand):
    help = (
        f'Generates a query set of {NUM_QUERIES} movie titles based on the number of votes. '
        f'Output is saved to {OUTPUT_FILE} in the project root.'
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting query set generation..."))

        # Fetch movies with their titles and number of votes from ratings
        # We only want movies that actually have a rating and num_votes > 0
        # We use select_related to fetch the related Movie object (and its primary_title)
        # efficiently along with the Rating object.
        movies_with_ratings = Rating.objects.filter(
            num_votes__isnull=False,
            num_votes__gt=0
        ).select_related('movie').only(
            'movie__primary_title', 'num_votes'
        )

        if not movies_with_ratings.exists():
            raise CommandError("No movies with ratings found in the database. Load data first or check your data.")

        self.stdout.write(f"Found {movies_with_ratings.count()} movies with ratings.")

        titles = []
        weights = [] # These will be the number of votes

        for rating_info in movies_with_ratings:
            # Ensure movie object and primary_title are accessible
            if rating_info.movie and rating_info.movie.primary_title:
                titles.append(rating_info.movie.primary_title)
                weights.append(rating_info.num_votes)
            else:
                self.stdout.write(self.style.WARNING(f"Skipping rating for tconst {rating_info.movie_id} due to missing movie or title data."))


        if not titles:
            raise CommandError("No valid titles could be extracted from movies with ratings.")

        self.stdout.write(f"Prepared {len(titles)} unique movie titles for sampling.")

        # Perform weighted random sampling
        # random.choices samples k elements from the population with replacement,
        # respecting the given weights.
        try:
            sampled_queries = random.choices(titles, weights=weights, k=NUM_QUERIES)
        except Exception as e:
            raise CommandError(f"Error during weighted random sampling: {e}")

        self.stdout.write(f"Successfully sampled {len(sampled_queries)} queries.")

        # Write the queries to the output file
        # Path(OUTPUT_FILE) will create the file in the directory where 'manage.py' is run.
        output_file_path = Path(OUTPUT_FILE)
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                for query in sampled_queries:
                    f.write(query + '\n')
        except IOError as e:
            raise CommandError(f"Error writing queries to file {output_file_path}: {e}")
        self.stdout.write(self.style.SUCCESS(f"Successfully generated {NUM_QUERIES} queries and saved to {output_file_path}"))
