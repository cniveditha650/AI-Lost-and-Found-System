================================================================
  AI-Based Lost & Found System
  Dataset: Delhi Metro Lost and Found (Kaggle)
================================================================

DATASET USED
  Name    : Delhi Metro Lost and Found Dataset
  Author  : forgetabhi
  Kaggle  : kaggle.com/datasets/forgetabhi/delhi-metro-lost-and-found-dataset
  Records : 13,000+ real lost item reports from Delhi Metro stations
  Format  : CSV (item name, category, station, date, status)
  Items   : Mobile phones, wallets, keys, bags, documents,
            jewelry, glasses — all mixed together randomly

HOW THE DATASET IS USED
  The CSV is loaded into our database as text records.
  Each record gets assigned to a category (electronics, wallet, etc.)
  by keyword-matching the item name.
  When a user reports an item:
    - If they upload a photo → AI image matching (color histogram)
    - If no photo → keyword search on the 13,000+ CSV records
  Results are ranked by similarity score.


SETUP STEPS (do these in order)
================================================================

STEP 1: Install Python 3.10+
  Download from python.org
  CHECK "Add Python to PATH" during install!

STEP 2: Open VS Code
  File > Open Folder > select the lost-found/ folder

STEP 3: Open Terminal in VS Code
  Press Ctrl + backtick (`)

STEP 4: Create virtual environment
  python -m venv venv

STEP 5: Activate virtual environment
  Windows:   venv\Scripts\activate
  Mac/Linux: source venv/bin/activate
  You should see (venv) in the terminal.

STEP 6: Install libraries
  pip install -r requirements.txt

STEP 7: Get your Kaggle API key
  a. Go to https://www.kaggle.com and create a free account
  b. Click your profile photo > Settings
  c. Scroll to API section > click "Create New Token"
  d. This downloads a file called kaggle.json
  e. Put kaggle.json in the lost-found/ folder (same folder as app.py)

STEP 8: Download dataset and populate database
  python load_dataset.py

  This will:
  - Download the Delhi Metro Lost & Found CSV from Kaggle (~2 MB)
  - Read all 13,000+ records
  - Map each item to a category automatically
  - Save all records to database.json
  - Show you a summary of how many items per category

STEP 9: Run the app
  python app.py

STEP 10: Open in browser
  http://127.0.0.1:5000


PROJECT STRUCTURE
================================================================
lost-found/
  app.py             <- Main Flask server + AI matching logic
  load_dataset.py    <- Downloads + imports Delhi Metro CSV
  requirements.txt   <- Python libraries to install
  database.json      <- Auto-created when dataset is loaded
  kaggle.json        <- Your Kaggle API key (you download this)
  uploads/           <- User-uploaded images stored here
  templates/
    base.html        <- Shared layout, navbar, styles
    index.html       <- Home page with stats
    report.html      <- Report a lost or found item
    browse.html      <- Browse + keyword + image search
    admin.html       <- Admin dashboard


APP PAGES
================================================================
  http://127.0.0.1:5000         Home page
  http://127.0.0.1:5000/report  Report lost or found item
  http://127.0.0.1:5000/browse  Search all 13,000+ records
  http://127.0.0.1:5000/admin   Admin panel


HOW AI MATCHING WORKS
================================================================
  TEXT MATCHING (always available):
    - Keywords from the user description are matched against
      all item records in the database
    - Items of the same category with overlapping keywords
      are returned as matches

  IMAGE MATCHING (when user uploads a photo):
    - Image is resized to 64x64 pixels
    - Color histogram extracted for R, G, B channels
    - Results in a 96-number "feature vector"
    - Cosine similarity compared against all items with images
    - Items above 78% similarity shown as matches

  The Delhi Metro dataset has NO images, so image matching
  only works between user-uploaded photos.
  Text matching works across all 13,000+ records.


COMMON PROBLEMS
================================================================
  "kaggle: command not found"
    Run: pip install kaggle

  "401 Unauthorized"
    Your kaggle.json is invalid. Re-download it from kaggle.com

  "ModuleNotFoundError"
    Make sure venv is activated: venv\Scripts\activate

  "Port already in use"
    Change app.run(debug=True) to app.run(debug=True, port=5001)

  "No records in database"
    Run: python load_dataset.py

  No kaggle account?
    Just run python load_dataset.py anyway.
    It will generate 200 realistic sample records as a fallback.
================================================================
