import gzip
import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, IntegrityError
from movies.models import Person, Movie, Rating, Principal # Adjust 'movies' if your app name is different
from dateutil.parser import isoparse # For parsing dates if needed, not directly used here

# Define file paths (these should point to your downloaded and unzipped TSV files)
# For simplicity, we assume files are in a 'data/' subdirectory of your project root.
# You MUST download these files from https://www.imdb.com/interfaces/
# and place them in the specified directory.
# Example: BASE_DIR / 'data' / 'name.basics.tsv'
# For this example, let's assume they are in a 'data' folder in the project root.
# You'll need to adjust these paths.
DATA_DIR = 'data/' # Create this directory and put TSV files in it.
NAME_BASICS_FILE = DATA_DIR + 'name.basics.tsv.gz'
TITLE_BASICS_FILE = DATA_DIR + 'title.basics.tsv.gz'
TITLE_RATINGS_FILE = DATA_DIR + 'title.ratings.tsv.gz'
TITLE_PRINCIPALS_FILE = DATA_DIR + 'title.principals.tsv.gz'

# Helper to convert TSV \N to None and handle integer conversion
def clean_value(value, value_type=str):
    if value == r'\N':
        return None
    try:
        return value_type(value)
    except ValueError:
        return None # Or raise error, or log

class Command(BaseCommand):
    help = 'Loads IMDb data from TSV files into the database. Ensure files are downloaded and paths are correct.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting IMDb data loading process..."))

        # It's crucial to load data in an order that respects foreign key constraints
        # 1. Persons (name.basics)
        # 2. Movies (title.basics)
        # 3. Ratings (title.ratings) - FK to Movie
        # 4. Principals (title.principals) - FK to Movie and Person

        self._load_persons()
        self._load_movies()
        self._load_ratings()
        self._load_principals()

        self.stdout.write(self.style.SUCCESS("Successfully loaded all IMDb data."))

    def _load_data_bulk(self, file_path, model_class, field_mapping, batch_size=10000, unique_field=None):
        """
        Generic function to load data in bulk from a gzipped TSV file.
        
        :param file_path: Path to the .tsv.gz file
        :param model_class: The Django model class to populate
        :param field_mapping: A dictionary mapping TSV header names to model field names and type converters
                              e.g., {'nconst': ('nconst', str), 'birthYear': ('birth_year', int)}
        :param batch_size: Number of records to create in each bulk_create call
        :param unique_field: The field name in the model that should be unique (e.g., 'nconst' or 'tconst')
        """
        self.stdout.write(f"Loading data for {model_class.__name__} from {file_path}...")
        count = 0
        loaded_count = 0
        skipped_count = 0
        batch = []
        
        # Get existing IDs if unique_field is provided, to avoid IntegrityError on re-runs for some models.
        # This is a simple check; for very large datasets, more sophisticated "upsert" logic might be needed
        # or ensure you run this on an empty database.
        existing_ids = set()
        if unique_field:
            self.stdout.write(f"Fetching existing IDs for {model_class.__name__}...")
            try:
                # Ensure unique_field is a string, not a tuple from field_mapping
                actual_unique_field_name = unique_field
                if isinstance(unique_field, tuple): # if it came from field_mapping.values()
                    actual_unique_field_name = unique_field[0]

                existing_ids = set(model_class.objects.values_list(actual_unique_field_name, flat=True))
                self.stdout.write(f"Found {len(existing_ids)} existing IDs for {model_class.__name__}.")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not fetch existing IDs for {model_class.__name__}: {e}"))


        try:
            with gzip.open(file_path, 'rt', encoding='utf-8') as tsvfile:
                reader = csv.DictReader(tsvfile, delimiter='\t')
                for row in reader:
                    count += 1
                    if count % (batch_size * 5) == 0: # Log progress less frequently
                        self.stdout.write(f"Processed {count} rows for {model_class.__name__} (Loaded: {loaded_count}, Skipped: {skipped_count})...")

                    # Check if record already exists (based on unique_field)
                    if unique_field:
                        # Ensure unique_field is a string, not a tuple from field_mapping
                        actual_unique_field_name = unique_field
                        if isinstance(unique_field, tuple): # if it came from field_mapping.values()
                            actual_unique_field_name = unique_field[0]
                        
                        record_id = clean_value(row.get(list(field_mapping.keys())[list(field_mapping.values()).index((actual_unique_field_name, str)) if (actual_unique_field_name, str) in field_mapping.values() else list(field_mapping.keys())[0]]), str) # Get the original TSV column name for the unique field
                        if record_id in existing_ids:
                            skipped_count +=1
                            continue
                    
                    obj_data = {}
                    valid_row = True
                    for tsv_header, (model_field, converter) in field_mapping.items():
                        raw_value = row.get(tsv_header)
                        cleaned = clean_value(raw_value, converter)
                        
                        # For boolean fields, IMDb uses '0' and '1'
                        if converter == bool:
                            cleaned = (raw_value == '1')

                        obj_data[model_field] = cleaned
                        
                        # If a primary key field is None after cleaning, this row is invalid
                        model_pk_field_name = model_class._meta.pk.name
                        if model_field == model_pk_field_name and cleaned is None:
                            self.stdout.write(self.style.WARNING(f"Skipping row due to None PK ({model_pk_field_name}): {row}"))
                            valid_row = False
                            break
                    
                    if not valid_row:
                        skipped_count += 1
                        continue

                    batch.append(model_class(**obj_data))
                    
                    if len(batch) >= batch_size:
                        try:
                            with transaction.atomic(): # Ensure all or nothing for the batch
                                model_class.objects.bulk_create(batch, ignore_conflicts=True) # ignore_conflicts can be useful if some non-PK constraint might be violated and you want to skip
                            loaded_count += len(batch)
                            if unique_field: # Add newly loaded IDs to existing_ids to prevent re-processing if script is complex
                                for item in batch:
                                     existing_ids.add(getattr(item, actual_unique_field_name))
                        except IntegrityError as e:
                            self.stdout.write(self.style.ERROR(f"Integrity error during bulk create for {model_class.__name__}: {e}. Items in batch: {len(batch)}"))
                            # Optionally, try to insert one by one to find the culprit, or log and skip batch
                            skipped_count += len(batch)
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Generic error during bulk create for {model_class.__name__}: {e}"))
                            skipped_count += len(batch)
                        batch = []

                # Load any remaining items in the batch
                if batch:
                    try:
                        with transaction.atomic():
                            model_class.objects.bulk_create(batch, ignore_conflicts=True)
                        loaded_count += len(batch)
                    except IntegrityError as e:
                        self.stdout.write(self.style.ERROR(f"Integrity error during final bulk create for {model_class.__name__}: {e}"))
                        skipped_count += len(batch)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Generic error during final bulk create for {model_class.__name__}: {e}"))
                        skipped_count += len(batch)


        except FileNotFoundError:
            raise CommandError(f"File not found: {file_path}. Please download it from IMDb interfaces and place it correctly.")
        except Exception as e:
            raise CommandError(f"An error occurred while processing {file_path}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Finished loading {model_class.__name__}. Total rows processed: {count}, Loaded: {loaded_count}, Skipped: {skipped_count}."))

    def _load_persons(self):
        field_mapping = {
            'nconst': ('nconst', str),
            'primaryName': ('primary_name', str),
            'birthYear': ('birth_year', int),
            'deathYear': ('death_year', int),
            'primaryProfession': ('primary_profession', str),
            # 'knownForTitles' is complex, handle via Principals or skip if not directly needed on Person model
        }
        # Person model has nconst as PK, so it's inherently unique.
        self._load_data_bulk(NAME_BASICS_FILE, Person, field_mapping, batch_size=20000, unique_field='nconst')

    def _load_movies(self):
        field_mapping = {
            'tconst': ('tconst', str),
            'titleType': ('title_type', str),
            'primaryTitle': ('primary_title', str),
            'originalTitle': ('original_title', str),
            'isAdult': ('is_adult', bool), # Special handling for '0'/'1' in _load_data_bulk
            'startYear': ('start_year', int),
            'endYear': ('end_year', int),
            'runtimeMinutes': ('runtime_minutes', int),
            'genres': ('genres', str),
        }
        # Movie model has tconst as PK.
        self._load_data_bulk(TITLE_BASICS_FILE, Movie, field_mapping, batch_size=10000, unique_field='tconst')

    def _load_ratings(self):
        # This requires Movie objects to exist.
        field_mapping = {
            'tconst': ('movie_id', str), # movie_id is the PK for Rating and FK to Movie's tconst
            'averageRating': ('average_rating', float),
            'numVotes': ('num_votes', int),
        }
        # Rating model has movie_id (tconst) as PK.
        # For ratings, we must ensure the movie (tconst) exists.
        # bulk_create with ignore_conflicts=True might skip if tconst doesn't exist due to FK constraint,
        # or fail if DB doesn't support it gracefully.
        # A more robust way for FKs is to fetch valid movie_ids first or handle IntegrityError carefully.
        # For simplicity, assuming movies are loaded.
        
        # Custom loading logic for ratings due to OneToOneField and FK.
        self.stdout.write(f"Loading data for Rating from {TITLE_RATINGS_FILE}...")
        count = 0
        loaded_count = 0
        skipped_due_to_missing_movie = 0
        skipped_other = 0
        batch_size=10000
        batch = []

        # Get all existing movie tconsts for validation
        self.stdout.write("Fetching existing movie tconsts for rating validation...")
        existing_movie_tconsts = set(Movie.objects.values_list('tconst', flat=True))
        self.stdout.write(f"Found {len(existing_movie_tconsts)} movie tconsts.")
        
        # Get existing rating tconsts to avoid duplicates if script is re-run
        existing_rating_tconsts = set(Rating.objects.values_list('movie_id', flat=True))
        self.stdout.write(f"Found {len(existing_rating_tconsts)} existing ratings.")

        try:
            with gzip.open(TITLE_RATINGS_FILE, 'rt', encoding='utf-8') as tsvfile:
                reader = csv.DictReader(tsvfile, delimiter='\t')
                for row in reader:
                    count += 1
                    if count % (batch_size * 10) == 0:
                        self.stdout.write(f"Processed {count} rating rows (Loaded: {loaded_count}, Skipped Missing Movie: {skipped_due_to_missing_movie}, Skipped Other: {skipped_other})...")

                    tconst = clean_value(row.get('tconst'), str)
                    if not tconst:
                        skipped_other += 1
                        continue
                    
                    if tconst in existing_rating_tconsts: # Already loaded
                        skipped_other +=1
                        continue

                    if tconst not in existing_movie_tconsts:
                        skipped_due_to_missing_movie += 1
                        continue # Skip if the movie doesn't exist

                    avg_rating = clean_value(row.get('averageRating'), float)
                    num_v = clean_value(row.get('numVotes'), int)

                    batch.append(Rating(movie_id=tconst, average_rating=avg_rating, num_votes=num_v))
                    
                    if len(batch) >= batch_size:
                        try:
                            with transaction.atomic():
                                Rating.objects.bulk_create(batch, ignore_conflicts=True) # True if movie_id is PK and you want to skip duplicates
                            loaded_count += len(batch)
                            for item in batch: existing_rating_tconsts.add(item.movie_id)
                        except IntegrityError as e: # Should be rare with pre-checks but good to have
                            self.stdout.write(self.style.ERROR(f"Integrity error for Rating: {e}"))
                            skipped_other += len(batch)
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Generic error for Rating: {e}"))
                            skipped_other += len(batch)
                        batch = []
                
                if batch: # final batch
                    try:
                        with transaction.atomic():
                            Rating.objects.bulk_create(batch, ignore_conflicts=True)
                        loaded_count += len(batch)
                    except IntegrityError as e:
                        self.stdout.write(self.style.ERROR(f"Integrity error for final Rating: {e}"))
                        skipped_other += len(batch)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Generic error for final Rating: {e}"))
                        skipped_other += len(batch)

        except FileNotFoundError:
            raise CommandError(f"File not found: {TITLE_RATINGS_FILE}.")
        except Exception as e:
            raise CommandError(f"An error occurred while processing {TITLE_RATINGS_FILE}: {e}")
        self.stdout.write(self.style.SUCCESS(f"Finished loading Rating. Total: {count}, Loaded: {loaded_count}, Skipped Missing Movie: {skipped_due_to_missing_movie}, Skipped Other: {skipped_other}."))


    def _load_principals(self):
        # This requires Movie and Person objects to exist.
        # title.principals.tsv: tconst, ordering, nconst, category, job, characters
        self.stdout.write(f"Loading data for Principal from {TITLE_PRINCIPALS_FILE}...")
        count = 0
        loaded_count = 0
        skipped_missing_fk = 0
        skipped_other = 0
        batch_size = 50000 # Principals table can be very large
        batch = []

        # Get all existing movie tconsts and person nconsts for validation
        self.stdout.write("Fetching existing movie tconsts and person nconsts for principal validation...")
        existing_movie_tconsts = set(Movie.objects.values_list('tconst', flat=True))
        existing_person_nconsts = set(Person.objects.values_list('nconst', flat=True))
        self.stdout.write(f"Found {len(existing_movie_tconsts)} movie tconsts and {len(existing_person_nconsts)} person nconsts.")

        try:
            with gzip.open(TITLE_PRINCIPALS_FILE, 'rt', encoding='utf-8') as tsvfile:
                reader = csv.DictReader(tsvfile, delimiter='\t')
                for row in reader:
                    count += 1
                    if count % (batch_size * 2) == 0: # Log progress
                        self.stdout.write(f"Processed {count} principal rows (Loaded: {loaded_count}, Skipped Missing FK: {skipped_missing_fk}, Skipped Other: {skipped_other})...")

                    tconst = clean_value(row.get('tconst'), str)
                    nconst = clean_value(row.get('nconst'), str)

                    if not tconst or not nconst:
                        skipped_other += 1
                        continue
                    
                    if tconst not in existing_movie_tconsts or nconst not in existing_person_nconsts:
                        skipped_missing_fk += 1
                        continue

                    ordering = clean_value(row.get('ordering'), int)
                    if ordering is None: # Ordering is part of the composite key in some interpretations
                        skipped_other += 1
                        continue
                    
                    category = clean_value(row.get('category'), str)
                    if not category: # Category is important
                        skipped_other +=1
                        continue

                    job = clean_value(row.get('job'), str)
                    characters = clean_value(row.get('characters'), str) # Keep as string, might be JSON array string

                    # Skip if any crucial part of a potential composite key is missing
                    # (movie_id, person_id, ordering, category)
                    # The unique_together in model handles db-level uniqueness.
                    # Here, we are just constructing the object.

                    batch.append(Principal(
                        movie_id=tconst,
                        person_id=nconst,
                        ordering=ordering,
                        category=category,
                        job=job,
                        characters=characters
                    ))
                    
                    if len(batch) >= batch_size:
                        try:
                            with transaction.atomic():
                                Principal.objects.bulk_create(batch, ignore_conflicts=True) # Relies on unique_together in model
                            loaded_count += len(batch)
                        except IntegrityError as e:
                             # This can happen if unique_together is violated and ignore_conflicts isn't fully effective
                             # or if there's another integrity issue.
                            self.stdout.write(self.style.WARNING(f"Integrity error for Principal batch (likely duplicate): {len(batch)} items. Skipping batch."))
                            skipped_other += len(batch)
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Generic error for Principal: {e}"))
                            skipped_other += len(batch)
                        batch = []
                
                if batch: # final batch
                    try:
                        with transaction.atomic():
                            Principal.objects.bulk_create(batch, ignore_conflicts=True)
                        loaded_count += len(batch)
                    except IntegrityError as e:
                        self.stdout.write(self.style.WARNING(f"Integrity error for final Principal batch: {len(batch)} items. Skipping batch."))
                        skipped_other += len(batch)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Generic error for final Principal: {e}"))
                        skipped_other += len(batch)

        except FileNotFoundError:
            raise CommandError(f"File not found: {TITLE_PRINCIPALS_FILE}.")
        except Exception as e:
            raise CommandError(f"An error occurred while processing {TITLE_PRINCIPALS_FILE}: {e}")
        self.stdout.write(self.style.SUCCESS(f"Finished loading Principal. Total: {count}, Loaded: {loaded_count}, Skipped Missing FK: {skipped_missing_fk}, Skipped Other: {skipped_other}."))

