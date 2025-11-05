from flask import Flask, render_template, request
import pandas as pd
import math
import re
from urllib.parse import quote, unquote
from collections import Counter

app = Flask(__name__)
CSV_PATH = '/home/iqbal/project/py/dataset/data.csv'
PAGE_SIZE = 20
SEARCH_COLUMNS = ['name', 'description', 'author', 'keywords', 'categories', 'repository', 'homepage']

def load_csv():
    return pd.read_csv(CSV_PATH)

@app.route('/')
def show_dataset():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '', type=str).strip()
    df = load_csv()
    # Filter search
    if q:
        def row_search(row):
            return any(q.lower() in str(row.get(col, '')).lower() for col in SEARCH_COLUMNS if col in row)
        df_search = df[df.apply(row_search, axis=1)]
    else:
        df_search = df
    total_data = len(df_search)
    total_pages = max(1, math.ceil(total_data / PAGE_SIZE))
    data = df_search.iloc[(page-1)*PAGE_SIZE : page*PAGE_SIZE].to_dict(orient='records')
    return render_template('dataset.html', data=data, page=page, total_pages=total_pages, q=q, filter_category=None)

@app.route('/statistik')
def statistik():
    df = load_csv()
    categories_counter = Counter()
    for cat_raw in df['categories'].dropna():
        splits = [x.strip() for x in re.split(r'[;,|]', str(cat_raw)) if x.strip()]
        for cat in splits:
            categories_counter[cat.lower()] += 1
    categories_stats = categories_counter.most_common()
    total_dataset = sum(categories_counter.values())
    return render_template('statistik.html', categories_stats=categories_stats, total_dataset=total_dataset)

@app.route('/kategori/<nama_kategori>')
def kategori_detail(nama_kategori):
    page = request.args.get('page', 1, type=int)
    nama_kategori_decoded = unquote(nama_kategori)
    df = load_csv()
    # Pastikan 'categories' ada
    if 'categories' in df:
        mask = df['categories'].apply(lambda x: nama_kategori_decoded.lower() in str(x).lower() if pd.notnull(x) else False)
        df_cat = df[mask]
    else:
        df_cat = df[[]]  # empty
    total_data = len(df_cat)
    total_pages = max(1, math.ceil(total_data / PAGE_SIZE))
    data = df_cat.iloc[(page-1)*PAGE_SIZE : page*PAGE_SIZE].to_dict(orient='records')
    return render_template('dataset.html', data=data, page=page, total_pages=total_pages, q='', filter_category=nama_kategori_decoded)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
