import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
import json
import os

# --- KONFIGURACJA ---
INPUT_FILE = "books_data.yaml"
BOOKS_JSON_FILE = "books_categorized.json"  # Path to books_categorized.json (relative to script dir or parent)
SMOOTHING_FACTOR = 400  # Jeszcze gładsze linie
COLOR_PALETTE = "Spectral"  # "Spectral", "viridis", "magma", "RdBu"
LABEL_YEAR = 2021.5  # W którym roku (mniej więcej) umieścić napisy


def load_data(filepath):
    """Wczytuje YAML i przygotowuje dane."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    flat_data = []
    for year, records in data.items():
        if records:
            for record in records:
                flat_data.append(
                    {
                        "year": year,
                        "category": record["kategoria"],
                        "count": record["ilosc"],
                    }
                )

    df = pd.DataFrame(flat_data)
    pivot_df = df.pivot_table(
        index="year", columns="category", values="count", aggfunc="sum"
    ).fillna(0)

    # Sortowanie: Kategorie o największej sumarycznej objętości w środku (często wygląda to lepiej w Streamgraph)
    # Ale standardowe sortowanie po wielkości też jest ok.
    sorted_cols = pivot_df.sum().sort_values(ascending=False).index
    pivot_df = pivot_df[sorted_cols]

    return pivot_df


def smooth_data(df, n_points):
    """Interpoluje dane (wygładzanie krawędzi)."""
    years = df.index.values
    categories = df.columns
    years_smooth = np.linspace(years.min(), years.max(), n_points)

    smooth_data_dict = {}
    for cat in categories:
        spl = make_interp_spline(years, df[cat], k=3)
        y_smooth = spl(years_smooth)
        y_smooth = np.clip(y_smooth, 0, None)
        smooth_data_dict[cat] = y_smooth

    return years_smooth, smooth_data_dict, categories


def get_label_y_position(poly_collection, target_x):
    """
    Oblicza środek wysokości danej warstwy (polygonu) w punkcie target_x.
    Jest to konieczne przy 'wiggle', bo warstwy nie zaczynają się od 0.
    """
    paths = poly_collection.get_paths()
    if not paths:
        return 0

    vertices = paths[0].vertices
    # Znajdujemy punkty wierzchołków, które są bardzo blisko naszego target_x
    # (tolerancja np. 0.05 roku)
    mask = np.abs(vertices[:, 0] - target_x) < 0.05
    relevant_y = vertices[mask, 1]

    if len(relevant_y) > 0:
        # Środek to średnia z Y górnego i Y dolnego w tym punkcie
        return np.mean(relevant_y)
    return None


def load_books_data(json_filepath):
    """Wczytuje dane o książkach z JSON."""
    with open(json_filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_books_for_category_year(books_data, year, category):
    """Zwraca listę książek dla danej kategorii i roku."""
    year_str = str(year)
    if year_str not in books_data:
        return []
    
    books = books_data[year_str].get("books", [])
    return [book for book in books if book.get("category") == category]


def calculate_wiggle_baseline(years, data_dict, category_names):
    """Oblicza baseline 'wiggle' dla streamgraph."""
    n_points = len(years)
    n_categories = len(category_names)
    
    # Inicjalizacja baseline
    baseline = np.zeros(n_points)
    
    # Obliczamy baseline jako średnią z wartości dla każdego punktu czasowego
    for i in range(n_points):
        values = [data_dict[cat][i] for cat in category_names]
        baseline[i] = -np.mean(values)
    
    return baseline


def plot_wiggle_streamgraph(years_smooth, data_dict, category_names):
    y_values = [data_dict[cat] for cat in category_names]

    plt.style.use("seaborn-v0_8-white")
    fig, ax = plt.subplots(figsize=(16, 9))

    # Kolory
    colors = sns.color_palette(COLOR_PALETTE, n_colors=len(category_names))

    # --- Rysowanie z baseline='wiggle' ---
    stacks = ax.stackplot(
        years_smooth,
        y_values,
        labels=category_names,
        colors=colors,
        baseline="wiggle",
        alpha=0.9,
    )

    # --- Inteligentne etykietowanie ---
    for idx, (cat, stack) in enumerate(zip(category_names, stacks)):
        # Pobieramy "grubość" kategorii w punkcie, gdzie chcemy dać napis
        # Musimy znaleźć indeks w tablicy years_smooth odpowiadający LABEL_YEAR
        x_idx = (np.abs(years_smooth - LABEL_YEAR)).argmin()
        thickness = y_values[idx][x_idx]

        if thickness > 1.0:  # Pokaż napis tylko jeśli kategoria jest dość gruba
            # Obliczamy pozycję Y wyciągając dane z narysowanego wielokąta
            text_y = get_label_y_position(stack, LABEL_YEAR)

            if text_y is not None:
                ax.text(
                    LABEL_YEAR,
                    text_y,
                    cat.upper(),
                    fontsize=10,
                    color="#333333",
                    fontweight="bold",
                    ha="center",
                    va="center",
                    alpha=0.95,
                    path_effects=[],
                )  # Można dodać obrys tekstu dla czytelności

    # Formatowanie
    ax.set_xlim(years_smooth.min(), years_smooth.max())
    ax.get_yaxis().set_visible(
        False
    )  # Ukrywamy oś Y, bo w 'wiggle' liczby nie mają znaczenia

    # Oś X (Lata)
    years_int = np.arange(int(years_smooth.min()), int(years_smooth.max()) + 1)
    ax.set_xticks(years_int)
    ax.tick_params(axis="x", colors="#888888", labelsize=12)  # Szare, subtelne lata

    # Pionowe linie siatki (subtelne)
    ax.grid(axis="x", linestyle=":", alpha=0.3, color="black")

    # Usuwamy ramki
    sns.despine(left=True, bottom=True, top=True, right=True)

    # Dynamiczny tytuł z latami z danych
    min_year = int(years_smooth.min())
    max_year = int(years_smooth.max())
    plt.title(
        f"Strumień przeczytanych książek ({min_year}-{max_year})",
        fontsize=18,
        pad=30,
        fontweight="bold",
        color="#333333",
    )
    plt.tight_layout()

    OUTPUT_NAME = "streamgraph_wiggle.png"
    plt.savefig(OUTPUT_NAME, dpi=300, bbox_inches="tight")
    print(f"Wygenerowano wykres: {OUTPUT_NAME}")
    plt.show()


def generate_interactive_html(years_smooth, data_dict, category_names, books_data):
    """Generuje interaktywny HTML z streamgraph używając Plotly."""
    # Wersja Plotly.js do użycia w CDN
    PLOTLY_VERSION = "2.35.3"
    
    # Kolory - używamy palety Spectral
    colors = sns.color_palette(COLOR_PALETTE, n_colors=len(category_names))
    colors_hex = [f"rgb({int(r*255)},{int(g*255)},{int(b*255)})" for r, g, b in colors]
    
    # Obliczamy baseline wiggle (średnia z wszystkich wartości, zanegowana)
    baseline = calculate_wiggle_baseline(years_smooth, data_dict, category_names)
    
    # Przygotowujemy dane dla każdej kategorii
    traces = []
    cumulative_bottom = baseline.copy()
    
    for idx, cat in enumerate(category_names):
        y_values = data_dict[cat]
        
        # Obliczamy górną i dolną krawędź warstwy
        y_top = cumulative_bottom + y_values
        y_bottom = cumulative_bottom
        
        # Tworzymy trace dla tej kategorii jako wypełniony obszar
        # Używamy Scatter z fill='toself' do stworzenia zamkniętego obszaru
        trace = go.Scatter(
            x=np.concatenate([years_smooth, years_smooth[::-1]]),
            y=np.concatenate([y_top, y_bottom[::-1]]),
            fill='toself',
            fillcolor=colors_hex[idx],
            line=dict(color=colors_hex[idx], width=0.5),
            name=cat,
            hovertemplate='<extra></extra>',  # Pusty template - wyłączamy domyślny tooltip, ale eventy działają
            showlegend=True,
            mode='lines',
        )
        traces.append(trace)
        
        # Aktualizujemy cumulative_bottom dla następnej warstwy
        cumulative_bottom = y_top.copy()
    
    # Tworzymy layout
    min_year = int(years_smooth.min())
    max_year = int(years_smooth.max())
    
    fig = go.Figure(data=traces)
    
    fig.update_layout(
        title={
            'text': f"Strumień przeczytanych książek ({min_year}-{max_year})",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#333333'}
        },
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)',
            gridwidth=1,
            griddash='dot',
            showline=False,
            tickmode='linear',
            tick0=min_year,
            dtick=1,
            range=[min_year - 0.5, max_year + 0.5],
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            showline=False,
            showticklabels=False,
            zeroline=False,
        ),
        hovermode='closest',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Arial, sans-serif", size=12),
        margin=dict(l=50, r=50, t=80, b=50),
        height=600,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02
        )
    )
    
    # Generujemy HTML z osadzonymi danymi
    plot_json = fig.to_json()
    books_json = json.dumps(books_data, ensure_ascii=False)
    categories_json = json.dumps(list(category_names), ensure_ascii=False)
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Strumień przeczytanych książek ({min_year}-{max_year})</title>
    <script src="https://cdn.plot.ly/plotly-{PLOTLY_VERSION}.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .hover-info {{
            position: fixed;
            background-color: rgba(255, 255, 255, 0.98);
            border: 2px solid #333;
            border-radius: 8px;
            padding: 15px;
            max-width: 400px;
            max-height: 500px;
            overflow-y: auto;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            z-index: 10000;
            display: none;
            font-size: 12px;
            line-height: 1.6;
            pointer-events: none;
        }}
        .hover-info h3 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #333;
            padding-bottom: 5px;
        }}
        .hover-info .book-item {{
            margin: 8px 0;
            padding: 5px;
            background-color: #f9f9f9;
            border-left: 3px solid #666;
            padding-left: 10px;
        }}
        .hover-info .book-author {{
            font-weight: bold;
            color: #555;
        }}
        .hover-info .book-title {{
            color: #777;
            font-style: italic;
        }}
        /* Ukrywamy domyślny tooltip Plotly, ale zachowujemy eventy hover */
        .js-plotly-plot .hoverlayer {{
            display: none !important;
        }}
        .js-plotly-plot .hovertext {{
            display: none !important;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div id="plotly-chart"></div>
    </div>
    <div id="hover-info" class="hover-info"></div>
    
    <script>
        // Osadzamy dane książek w JavaScript
        const booksData = {books_json};
        
        // Lista kategorii w kolejności jak na wykresie
        const categories = {categories_json};
        
        // Dane wykresu
        const plotData = {plot_json};
        
        // Renderujemy wykres
        Plotly.newPlot('plotly-chart', plotData.data, plotData.layout, {{responsive: true}});
        
        // Obsługa hover
        const hoverInfo = document.getElementById('hover-info');
        const plotDiv = document.getElementById('plotly-chart');
        
        plotDiv.on('plotly_hover', function(data) {{
            if (data.points.length === 0) return;
            
            const point = data.points[0];
            
            // Pobieramy kategorię z nazwy trace'a lub z indeksu
            let category = point.fullData ? point.fullData.name : null;
            if (!category && point.curveNumber !== undefined && categories[point.curveNumber]) {{
                category = categories[point.curveNumber];
            }}
            
            if (!category) {{
                console.warn('No category found for point:', point);
                return;
            }}
            
            // Znajdujemy najbliższy rok z dostępnych lat w booksData
            const hoverYear = point.x;
            const availableYears = Object.keys(booksData).map(y => parseInt(y)).sort((a, b) => a - b);
            let closestYear = availableYears[0];
            let minDiff = Math.abs(hoverYear - closestYear);
            
            for (let i = 0; i < availableYears.length; i++) {{
                const diff = Math.abs(hoverYear - availableYears[i]);
                if (diff < minDiff) {{
                    minDiff = diff;
                    closestYear = availableYears[i];
                }}
            }}
            
            const yearStr = closestYear.toString();
            
            // Pobieramy książki dla tej kategorii i roku
            let books = [];
            if (booksData[yearStr] && booksData[yearStr].books) {{
                books = booksData[yearStr].books.filter(book => book.category === category);
            }}
            
            // Debug info
            console.log('Hover:', {{
                category: category,
                hoverYear: hoverYear,
                closestYear: closestYear,
                yearStr: yearStr,
                booksFound: books.length,
                availableYears: availableYears.length
            }});
            
            // Tworzymy overlay z książkami
            let html = `<h3>${{category.toUpperCase()}} - ${{closestYear}}</h3>`;
            html += `<p><strong>Ilość książek: ${{books.length}}</strong></p>`;
            
            if (books.length > 0) {{
                html += '<div style="margin-top: 10px;">';
                books.forEach(book => {{
                    html += `
                        <div class="book-item">
                            <div class="book-author">${{book.author}}</div>
                            <div class="book-title">${{book.title}}</div>
                        </div>
                    `;
                }});
                html += '</div>';
            }} else {{
                html += '<p style="color: #999; font-style: italic;">Brak książek w tej kategorii dla tego roku</p>';
            }}
            
            hoverInfo.innerHTML = html;
            hoverInfo.style.display = 'block';
            
            // Pozycjonowanie względem kursora
            const event = data.event || window.event;
            if (event) {{
                hoverInfo.style.left = (event.clientX + 20) + 'px';
                hoverInfo.style.top = (event.clientY + 20) + 'px';
            }}
        }});
        
        plotDiv.on('plotly_unhover', function(data) {{
            hoverInfo.style.display = 'none';
        }});
        
        // Aktualizacja pozycji hover info podczas ruchu myszy
        document.addEventListener('mousemove', function(e) {{
            if (hoverInfo.style.display === 'block') {{
                hoverInfo.style.left = (e.clientX + 20) + 'px';
                hoverInfo.style.top = (e.clientY + 20) + 'px';
            }}
        }});
    </script>
</body>
</html>"""
    
    # Zapisujemy HTML
    output_file = "streamgraph_interactive.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Wygenerowano interaktywny wykres: {output_file}")


# --- URUCHOMIENIE ---
if __name__ == "__main__":
    df = load_data(INPUT_FILE)
    x_smooth, y_smooth_dict, cats = smooth_data(df, SMOOTHING_FACTOR)
    
    # Generujemy statyczny wykres PNG
    plot_wiggle_streamgraph(x_smooth, y_smooth_dict, cats)
    
    # Generujemy interaktywny wykres HTML
    # Sprawdzamy kilka możliwych ścieżek do books_categorized.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(script_dir, BOOKS_JSON_FILE),  # W tym samym katalogu co skrypt
        os.path.join(os.path.dirname(script_dir), BOOKS_JSON_FILE),  # W katalogu nadrzędnym
        os.path.join(script_dir, "..", BOOKS_JSON_FILE),  # Względna ścieżka
    ]
    
    books_data_path = None
    for path in possible_paths:
        if os.path.exists(path):
            books_data_path = path
            break
    
    if books_data_path:
        books_data = load_books_data(books_data_path)
        generate_interactive_html(x_smooth, y_smooth_dict, cats, books_data)
    else:
        print(f"Ostrzeżenie: Nie znaleziono pliku books_categorized.json w żadnej z lokalizacji:")
        for path in possible_paths:
            print(f"  - {path}")
        print("Pomijam generowanie interaktywnego HTML")
