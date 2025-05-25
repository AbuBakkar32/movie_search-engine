# IMDb Movie Search Engine

## Description
This project is a Django-based web application that allows users to search for movies and view details from a local copy of the IMDb dataset.

## Features
- Search for movies by title.
- View detailed information about movies, including cast, crew, ratings, and more.
- (Potentially, depending on implementation) Filter and sort search results.
- (Potentially, depending on implementation) User authentication and personalized lists.

## Installation
1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd movie_search-engine
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt  # Assuming a requirements.txt file exists or will be created
   ```
4. **Set up the database:**
   - The project uses SQLite by default.
   - Run migrations:
     ```bash
     python manage.py migrate
     ```
5. **Load IMDb Data:**
   - This project requires IMDb dataset files (e.g., `title.basics.tsv`, `name.basics.tsv`, `title.principals.tsv`, `title.ratings.tsv`).
   - Place the TSV files in a designated directory (e.g., `data/`).
   - Run the data loading script:
     ```bash
     python manage.py load_imdb_data <path_to_tsv_files_directory>
     ```
     *(Note: The exact command and script name `load_imdb_data` are based on the file `movies/management/commands/load_imdb_data.py` found in the codebase. If this script requires specific file names or a different directory structure, this section should be updated.)*
6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```
   The application will be accessible at `http://127.0.0.1:8000/`.

## Usage
- Access the application through your web browser.
- Use the search bar to find movies.
- Click on movie titles to see more details.

### Management Commands
- `python manage.py load_imdb_data <path_to_tsv_files_directory>`: Loads data from IMDb TSV files into the database.
- `python manage.py generate_query_set`: (Purpose of this script needs to be determined from its content or further context to be accurately documented here. It's found in `movies/management/commands/generate_query_set.py`.)

## Data Source
This application uses data from IMDb (Internet Movie Database). The data is typically distributed in TSV (Tab Separated Values) format. You will need to download the relevant dataset files from IMDb Datasets (https://developer.imdb.com/non-commercial-datasets/) to populate the database.

The key files used are:
- `name.basics.tsv`: Contains information about people (actors, directors, etc.).
- `title.basics.tsv`: Contains information about titles (movies, TV shows, etc.).
- `title.ratings.tsv`: Contains rating information for titles.
- `title.principals.tsv`: Contains information about the principal cast and crew for titles.

## Models
The application uses the following Django models (defined in `movies/models.py`):

- **`Person`**: Represents an individual (actor, director, writer, etc.). Corresponds to `name.basics.tsv`.
  - Fields: `nconst` (PK), `primary_name`, `birth_year`, `death_year`, `primary_profession`.
- **`Movie`**: Represents a movie, TV show, or other title. Corresponds to `title.basics.tsv`.
  - Fields: `tconst` (PK), `title_type`, `primary_title`, `original_title`, `is_adult`, `start_year`, `end_year`, `runtime_minutes`, `genres`.
  - Relationships: `principals` (ManyToMany with `Person` through `Principal`).
- **`Rating`**: Stores IMDb rating information for a movie. Corresponds to `title.ratings.tsv`.
  - Fields: `movie` (OneToOne with `Movie`, PK), `average_rating`, `num_votes`.
- **`Principal`**: Represents the association between a `Movie` and a `Person` for a specific role or job (e.g., actor in a movie, director of a movie). Corresponds to `title.principals.tsv`.
  - Fields: `movie` (FK to `Movie`), `person` (FK to `Person`), `ordering`, `category`, `job`, `characters`.
  - Meta: `unique_together` on (`movie`, `person`, `ordering`, `category`).

*(Note: This README assumes the project structure and commands as observed. It might need adjustments if there's a `requirements.txt` file or if the `generate_query_set.py` script has a specific user-facing purpose.)*