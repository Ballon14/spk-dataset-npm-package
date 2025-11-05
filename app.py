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

# Struktur data rekomendasi, akan dipakai di halaman rekomendasi
PACKAGE_RECOMMENDATIONS = {
    "Website": {
        "main": {"name": "Django", "desc": "Web framework powerful, full-featured, cocok untuk project besar & kecil."},
        "alternatives": [
            {"name": "Flask", "desc": "Microframework ringan dan fleksibel."},
            {"name": "FastAPI", "desc": "Modern, cepat, unggul untuk API."}
        ]
    },
    "API": {
        "main": {"name": "FastAPI", "desc": "Framework modern dan sangat cepat untuk building API."},
        "alternatives": [
            {"name": "Flask", "desc": "Popular, simple, mudah dipelajari."}
        ]
    },
    "Data Science": {
        "main": {"name": "pandas", "desc": "Library powerful untuk data analysis."},
        "alternatives": [
            {"name": "numpy", "desc": "Support komputasi numerik."},
            {"name": "dask", "desc": "Pemrosesan data besar."}
        ]
    },
    "Machine Learning": {
        "main": {"name": "scikit-learn", "desc": "Library ML umum, mudah digunakan untuk berbagai algoritma."},
        "alternatives": [
            {"name": "TensorFlow", "desc": "Powerful, scalable untuk deep learning."},
            {"name": "PyTorch", "desc": "Populer untuk riset & aplikasi deep learning."}
        ]
    },
    # Tambahkan kategori lain sesuai kebutuhan
}

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
    # Hitung total download last month
    if 'downloads_last_month' in df.columns:
        total_download_last_month = df['downloads_last_month'].fillna(0).sum()
        # Top 10 package download terbanyak
        top_downloaded_packages = (
            df[['name','downloads_last_month']]
            .dropna(subset=['downloads_last_month'])
            .sort_values('downloads_last_month', ascending=False)
            .head(10)
            .to_dict(orient='records')
        )
    else:
        total_download_last_month = 0
        top_downloaded_packages = []
    for cat_raw in df['categories'].dropna():
        splits = [x.strip() for x in re.split(r'[;,|]', str(cat_raw)) if x.strip()]
        for cat in splits:
            categories_counter[cat.lower()] += 1
    categories_stats = categories_counter.most_common()
    total_dataset = sum(categories_counter.values())
    return render_template(
        'statistik.html',
        categories_stats=categories_stats,
        total_dataset=total_dataset,
        total_download_last_month=total_download_last_month,
        top_downloaded_packages=top_downloaded_packages
    )

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

@app.route('/rekomendasi')
def rekomendasi():
    import pandas as pd  # Local import supaya cepat reload
    kategori = request.args.get('kategori', type=str)
    df = load_csv()
    # Ambil semua kategori unik (split, normalisasi, sort)
    cat_set = set()
    for catlist in df['categories'].dropna():
        for cat in [x.strip() for x in str(catlist).split(',') if x.strip()]:
            cat_set.add(cat)
    kategori_list = sorted(cat_set)
    rekomendasi_data = None
    if kategori:
        # Cari semua baris yang categories-nya memuat kategori tsb (case insensitive)
        mask = df['categories'].apply(lambda x: kategori.lower() in str(x).lower() if pd.notnull(x) else False)
        dfcat = df[mask]
        # Urutkan berdasarkan downloads_last_month (desc), null jd 0
        dfcat['downloads_last_month'] = pd.to_numeric(dfcat['downloads_last_month'], errors='coerce').fillna(0)
        top = dfcat.sort_values('downloads_last_month', ascending=False).head(4)
        packages = top.to_dict(orient='records')
        if packages:
            rekomendasi_data = {
                'utama': packages[0],
                'alternatif': packages[1:] if len(packages) > 1 else []
            }
    return render_template(
        'rekomendasi.html',
        kategori_list=kategori_list,
        kategori_terpilih=kategori,
        rekomendasi_data=rekomendasi_data
    )

@app.route('/package/<path:name>')
def detail_package(name):
    import pandas as pd
    # decode jika pakai spasi/encode url
    from urllib.parse import unquote
    name_dec = unquote(name)
    df = load_csv()
    # Filter persis nama package
    pkgrow = df[df['name'] == name_dec]
    if pkgrow.empty:
        return render_template('detail_package.html', package=None, name=name_dec)
    pkg = pkgrow.iloc[0].to_dict()
    return render_template('detail_package.html', package=pkg, name=name_dec)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
