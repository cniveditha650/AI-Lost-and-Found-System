"""
============================================================
  DATASET LOADER
  Dataset : Delhi Metro Lost and Found
  Kaggle  : kaggle.com/datasets/forgetabhi/delhi-metro-lost-and-found-dataset
  Records : 13,000+ real lost item reports
  Type    : CSV (text data — item name, category, station, date)

  This dataset has NO images — it has real text descriptions
  of lost items reported at Delhi Metro stations.
  We import all 13,000 records into our database as text entries.
  When a user uploads an image, the AI image matching works on top.

  HOW TO RUN:
    Step 1: kaggle.com → free account
    Step 2: Profile → Settings → API → Create New Token → kaggle.json
    Step 3: Put kaggle.json in this folder
    Step 4: pip install -r requirements.txt
    Step 5: python load_dataset.py
    Step 6: python app.py
============================================================
"""

import os, json, uuid, shutil, subprocess, csv, random
from datetime import datetime, timedelta

DB_FILE    = 'database.json'
DATASET_DIR = 'kaggle_datasets/delhi_metro'
os.makedirs(DATASET_DIR, exist_ok=True)

# ── Category mapping from Delhi dataset → our app categories ──
# The Delhi dataset uses item names like "Mobile Phone", "Wallet", etc.
# We map them to our fixed category list.
CATEGORY_MAP = {
    # Electronics
    'mobile': 'electronics', 'phone': 'electronics', 'iphone': 'electronics',
    'samsung': 'electronics', 'smartphone': 'electronics', 'charger': 'electronics',
    'laptop': 'electronics', 'tablet': 'electronics', 'ipad': 'electronics',
    'earphone': 'electronics', 'headphone': 'electronics', 'airpods': 'electronics',
    'camera': 'electronics', 'watch': 'electronics', 'smartwatch': 'electronics',
    'powerbank': 'electronics', 'power bank': 'electronics', 'pendrive': 'electronics',
    'pen drive': 'electronics', 'hard disk': 'electronics', 'cable': 'electronics',

    # Wallet / Purse
    'wallet': 'wallet', 'purse': 'wallet', 'handbag': 'wallet',
    'clutch': 'wallet', 'card': 'wallet', 'pouch': 'wallet',
    'money': 'wallet', 'cash': 'wallet',

    # Keys
    'key': 'keys', 'keys': 'keys', 'keychain': 'keys',
    'car key': 'keys', 'bike key': 'keys',

    # Bags
    'bag': 'bag', 'backpack': 'bag', 'luggage': 'bag',
    'suitcase': 'bag', 'trolley': 'bag', 'briefcase': 'bag',
    'school bag': 'bag', 'office bag': 'bag', 'laptop bag': 'bag',

    # Clothing
    'jacket': 'clothing', 'coat': 'clothing', 'shirt': 'clothing',
    'jeans': 'clothing', 'trouser': 'clothing', 'clothes': 'clothing',
    'dress': 'clothing', 'saree': 'clothing', 'dupatta': 'clothing',
    'shawl': 'clothing', 'scarf': 'clothing', 'sweater': 'clothing',
    'hoodie': 'clothing', 'cap': 'clothing', 'hat': 'clothing',
    'shoe': 'clothing', 'sandal': 'clothing', 'slipper': 'clothing',
    'belt': 'clothing', 'gloves': 'clothing', 'mask': 'clothing',

    # Documents
    'passport': 'documents', 'document': 'documents', 'aadhaar': 'documents',
    'aadhar': 'documents', 'pan card': 'documents', 'id card': 'documents',
    'driving license': 'documents', 'certificate': 'documents',
    'admit card': 'documents', 'marksheet': 'documents',
    'cheque': 'documents', 'checkbook': 'documents', 'book': 'documents',
    'notebook': 'documents', 'diary': 'documents', 'file': 'documents',

    # Jewelry
    'ring': 'jewelry', 'necklace': 'jewelry', 'chain': 'jewelry',
    'bangle': 'jewelry', 'bracelet': 'jewelry', 'earring': 'jewelry',
    'pendant': 'jewelry', 'jewellery': 'jewelry', 'jewelry': 'jewelry',
    'gold': 'jewelry', 'silver': 'jewelry', 'locket': 'jewelry',

    # Glasses
    'glasses': 'glasses', 'spectacles': 'glasses', 'sunglasses': 'glasses',
    'specs': 'glasses', 'eyewear': 'glasses', 'goggles': 'glasses',

    # Other common items
    'umbrella': 'other', 'water bottle': 'other', 'bottle': 'other',
    'tiffin': 'other', 'lunchbox': 'other', 'lunch box': 'other',
    'toy': 'other', 'ball': 'other', 'pen': 'other', 'pencil': 'other',
    'calculator': 'other', 'thermometer': 'other', 'medicine': 'other',
    'instrument': 'other', 'sports': 'other', 'gym': 'other',
}

# Delhi Metro stations (for location field)
DELHI_METRO_STATIONS = [
    "Rajiv Chowk Metro Station", "Kashmere Gate Metro Station",
    "New Delhi Metro Station", "Chandni Chowk Metro Station",
    "Connaught Place Metro Station", "AIIMS Metro Station",
    "Hauz Khas Metro Station", "Saket Metro Station",
    "Dwarka Sector 21 Metro Station", "Noida City Centre Metro Station",
    "Vaishali Metro Station", "Anand Vihar Metro Station",
    "Inderlok Metro Station", "Rohini West Metro Station",
    "Pitampura Metro Station", "Janakpuri West Metro Station",
    "Uttam Nagar East Metro Station", "Dwarka Mor Metro Station",
    "IGI Airport Metro Station", "Aerocity Metro Station",
    "Okhla Metro Station", "Lajpat Nagar Metro Station",
    "Central Secretariat Metro Station", "Barakhamba Road Metro Station",
    "Mandi House Metro Station", "ITO Metro Station",
    "Welcome Metro Station", "Yamuna Bank Metro Station",
]

def guess_category(item_name: str) -> str:
    """Guess our category from the item name string."""
    name_lower = item_name.lower().strip()
    # Try longest keyword match first
    for keyword in sorted(CATEGORY_MAP.keys(), key=len, reverse=True):
        if keyword in name_lower:
            return CATEGORY_MAP[keyword]
    return 'other'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {"items": []}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def random_date_in_range(start_year=2022, end_year=2024):
    start = datetime(start_year, 1, 1)
    end   = datetime(end_year, 12, 31)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).isoformat()

# ── STEP 1: Setup Kaggle credentials ──────────────────────────
def setup_kaggle():
    kaggle_dir = os.path.expanduser('~/.kaggle')
    os.makedirs(kaggle_dir, exist_ok=True)
    if os.path.exists('kaggle.json'):
        dest = os.path.join(kaggle_dir, 'kaggle.json')
        shutil.copy('kaggle.json', dest)
        try: os.chmod(dest, 0o600)
        except: pass
        print('✅ kaggle.json configured!\n')
        return True
    print('❌  kaggle.json NOT found!\n')
    print('  How to get it:')
    print('  1. Go to https://www.kaggle.com → free signup')
    print('  2. Click profile photo → Settings')
    print('  3. Scroll to API section → click Create New Token')
    print('  4. Put the downloaded kaggle.json in this folder')
    print('  5. Run this script again\n')
    return False

# ── STEP 2: Download the dataset ──────────────────────────────
def download_dataset():
    print('📥 Downloading: Delhi Metro Lost and Found Dataset')
    print('   kaggle.com/datasets/forgetabhi/delhi-metro-lost-and-found-dataset')
    print('   13,000+ real lost item records — CSV format\n')
    result = subprocess.run(
        ['kaggle', 'datasets', 'download',
         '-d', 'forgetabhi/delhi-metro-lost-and-found-dataset',
         '-p', DATASET_DIR, '--unzip'],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f'✅ Downloaded to: {DATASET_DIR}\n')
        return True
    print(f'❌ Download failed: {result.stderr.strip()[:200]}\n')
    return False

# ── STEP 3: Find the CSV file ─────────────────────────────────
def find_csv():
    for root, _, files in os.walk(DATASET_DIR):
        for f in files:
            if f.endswith('.csv'):
                return os.path.join(root, f)
    return None

# ── STEP 4: Inspect CSV columns ───────────────────────────────
def inspect_csv(csv_path):
    """Print the first 3 rows so we can see what columns exist."""
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            if i >= 3: break
            rows.append(dict(row))
    print('📄 CSV columns found:')
    if rows:
        for col in rows[0].keys():
            print(f'   • {col}')
    print()
    return rows[0].keys() if rows else []

# ── STEP 5: Import CSV rows into database ─────────────────────
def import_csv(csv_path, columns):
    """
    The Delhi Metro dataset CSV has columns like:
      Sr_No, Item_Name, Item_Category, Description,
      Station_Name, Date_Found, Time_Found, Status, Contact

    We map these into our database format.
    The script is flexible — it tries multiple possible column names.
    """
    print('📦 Importing records from CSV...')

    # Flexible column name resolution
    col = list(columns)
    col_lower = [c.lower().strip() for c in col]

    def find_col(*candidates):
        for c in candidates:
            for i, cl in enumerate(col_lower):
                if c in cl:
                    return col[i]
        return None

    item_name_col  = find_col('item_name', 'item name', 'name', 'article', 'object')
    category_col   = find_col('category', 'item_category', 'type')
    desc_col       = find_col('description', 'desc', 'detail', 'remark')
    station_col    = find_col('station', 'location', 'place', 'found_at', 'lost_at')
    date_col       = find_col('date', 'found_date', 'lost_date', 'date_found')
    status_col     = find_col('status', 'state', 'current')
    contact_col    = find_col('contact', 'phone', 'email', 'mobile')

    print(f'   Mapped columns:')
    print(f'   Item name → {item_name_col}')
    print(f'   Category  → {category_col}')
    print(f'   Description → {desc_col}')
    print(f'   Station   → {station_col}')
    print(f'   Date      → {date_col}')
    print()

    db = load_db()
    # Remove any old delhi_metro entries before re-importing
    db['items'] = [i for i in db['items'] if i.get('source') != 'delhi_metro']

    added = 0
    skipped = 0
    category_counts = {}

    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Shuffle so items appear random order in the app
    random.shuffle(rows)

    for row in rows:
        # Get item name
        item_name = ''
        if item_name_col and item_name_col in row:
            item_name = str(row[item_name_col]).strip()
        if not item_name or item_name.lower() in ('nan', 'none', ''):
            skipped += 1
            continue

        # Guess category
        csv_category = ''
        if category_col and category_col in row:
            csv_category = str(row[category_col]).strip()
        category = guess_category(item_name + ' ' + csv_category)

        # Description
        description = item_name
        if desc_col and desc_col in row:
            extra = str(row[desc_col]).strip()
            if extra and extra.lower() not in ('nan', 'none', '-', ''):
                description = f"{item_name} — {extra}"

        # Location (station)
        location = random.choice(DELHI_METRO_STATIONS)
        if station_col and station_col in row:
            st = str(row[station_col]).strip()
            if st and st.lower() not in ('nan', 'none', '-', ''):
                location = st + ' Metro Station' if 'metro' not in st.lower() else st

        # Date
        date_str = datetime.now().strftime('%Y-%m-%d')
        if date_col and date_col in row:
            raw_date = str(row[date_col]).strip()
            if raw_date and raw_date.lower() not in ('nan', 'none', ''):
                date_str = raw_date[:10]  # Take first 10 chars (YYYY-MM-DD)

        # Status from dataset → map to our 'open'/'resolved'
        status = 'open'
        if status_col and status_col in row:
            s = str(row[status_col]).strip().lower()
            if any(x in s for x in ['return', 'claim', 'resolv', 'close', 'handover']):
                status = 'resolved'

        # Type: Delhi dataset is "found" items (items found at stations)
        # We mark some as 'lost' randomly for demo variety
        item_type = 'found' if random.random() > 0.35 else 'lost'

        # Fake contact info (real data privacy)
        fake_name  = random.choice(FAKE_NAMES)
        fake_email = fake_name.lower().replace(' ', '.') + str(random.randint(10, 99)) + '@example.com'

        category_counts[category] = category_counts.get(category, 0) + 1

        db['items'].append({
            'id':          str(uuid.uuid4())[:8].upper(),
            'type':        item_type,
            'name':        fake_name,
            'email':       fake_email,
            'category':    category,
            'description': description,
            'location':    location,
            'date':        date_str,
            'image':       None,
            'features':    None,
            'status':      status,
            'created_at':  random_date_in_range(),
            'source':      'delhi_metro',
            'original_item': item_name,
        })
        added += 1

    save_db(db)

    print(f'✅ Imported {added} records  |  Skipped {skipped} empty rows\n')
    print('📊 Items by category:')
    for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
        bar = '█' * min(cnt // 10, 40)
        print(f'   {cat:15s} {bar} {cnt}')
    print()
    return added

FAKE_NAMES = [
    'Amit Sharma', 'Priya Singh', 'Rahul Verma', 'Sunita Gupta',
    'Ravi Kumar', 'Neha Joshi', 'Suresh Patel', 'Anita Reddy',
    'Vikram Nair', 'Pooja Mehta', 'Arjun Das', 'Kavita Bhat',
    'Rohit Tiwari', 'Divya Rao', 'Sanjay Pillai', 'Meena Iyer',
    'Mohammed Farouk', 'Deepika Bansal', 'Nikhil Mishra', 'Geeta Agarwal',
    'Harish Chandra', 'Rekha Nanda', 'Sandeep Malik', 'Usha Pandey',
    'Arun Kapoor', 'Seema Saxena', 'Vijay Bhatnagar', 'Lalita Chopra',
    'Prakash Srivastava', 'Nirmala Devi', 'Ashok Chauhan', 'Sarla Yadav',
]

# ── MAIN ──────────────────────────────────────────────────────
if __name__ == '__main__':
    print('=' * 60)
    print('  AI Lost & Found — Dataset Loader')
    print('  Dataset: Delhi Metro Lost and Found (Kaggle)')
    print('=' * 60)
    print()

    kaggle_ok = setup_kaggle()
    total = 0

    if kaggle_ok:
        try:
            import kaggle as _
            if download_dataset():
                csv_path = find_csv()
                if csv_path:
                    print(f'📄 Found CSV: {csv_path}\n')
                    columns = inspect_csv(csv_path)
                    total   = import_csv(csv_path, columns)
                else:
                    print('❌ No CSV file found in downloaded dataset.')
        except ImportError:
            print('❌  kaggle library not installed.')
            print('    Fix: pip install kaggle\n')

    if total == 0:
        print('⚠️  Kaggle import failed or skipped.')
        print('   Generating realistic sample data instead...\n')
        total = generate_sample_data()

    db = load_db()
    print(f'✅ Database ready: {len(db["items"])} total items')
    print()
    print('Now run:  python app.py')
    print('Open:     http://127.0.0.1:5000')
    print('=' * 60)


def generate_sample_data():
    """Generates 200 realistic sample records if Kaggle download fails."""
    db = load_db()
    if any(i.get('source') == 'sample' for i in db['items']):
        print('ℹ️  Sample data already loaded.\n')
        return 0

    SAMPLE_ITEMS = [
        ('Mobile Phone - Samsung Galaxy', 'electronics'),
        ('iPhone 13 Pro Max', 'electronics'),
        ('OnePlus Nord smartwatch', 'electronics'),
        ('Boat earphones in black case', 'electronics'),
        ('Dell laptop power adapter', 'electronics'),
        ('Sony wireless headphones', 'electronics'),
        ('Brown leather wallet with cards', 'wallet'),
        ('Black purse with zipper', 'wallet'),
        ('Ladies handbag red color', 'wallet'),
        ('Card holder with driving license', 'wallet'),
        ('Honda City car keys with remote', 'keys'),
        ('Set of 4 keys on Superman keychain', 'keys'),
        ('Bike key Hero Splendor', 'keys'),
        ('Yale house key with green cap', 'keys'),
        ('Wildcraft blue backpack 40L', 'bag'),
        ('Black office laptop bag', 'bag'),
        ('Trolley bag hard shell 20 inch', 'bag'),
        ('Gym bag blue Nike brand', 'bag'),
        ('Grey hoodie IIT Delhi', 'clothing'),
        ('Black winter jacket with hood', 'clothing'),
        ('Blue checked formal shirt size L', 'clothing'),
        ('White salwar kameez with dupatta', 'clothing'),
        ('Indian passport in green cover', 'documents'),
        ('Aadhaar and PAN card in pouch', 'documents'),
        ('University degree certificate', 'documents'),
        ('Gold chain with Ganesh pendant', 'jewelry'),
        ('Silver bracelet with name engraved', 'jewelry'),
        ('Diamond ring white gold band', 'jewelry'),
        ('Ray-Ban aviator sunglasses gold', 'glasses'),
        ('Reading glasses round black frame', 'glasses'),
        ('Blue Milton water bottle 1L', 'other'),
        ('Compact umbrella dark blue', 'other'),
        ('Steel tiffin box 3 compartments', 'other'),
    ]

    added = 0
    for desc, cat in SAMPLE_ITEMS * 6:  # repeat to get ~200
        name = random.choice(FAKE_NAMES)
        db['items'].append({
            'id':          str(uuid.uuid4())[:8].upper(),
            'type':        random.choice(['lost', 'found']),
            'name':        name,
            'email':       name.lower().replace(' ', '.') + '@example.com',
            'category':    cat,
            'description': desc,
            'location':    random.choice(DELHI_METRO_STATIONS),
            'date':        datetime.now().strftime('%Y-%m-%d'),
            'image':       None,
            'features':    None,
            'status':      random.choice(['open', 'open', 'open', 'resolved']),
            'created_at':  random_date_in_range(),
            'source':      'sample',
        })
        added += 1

    random.shuffle(db['items'])
    save_db(db)
    print(f'✅ Generated {added} sample records\n')
    return added
