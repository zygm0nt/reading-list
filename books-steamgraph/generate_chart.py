import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
import seaborn as sns

# --- KONFIGURACJA ---
INPUT_FILE = "books_data.yaml"
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


# --- URUCHOMIENIE ---
if __name__ == "__main__":
    df = load_data(INPUT_FILE)
    x_smooth, y_smooth_dict, cats = smooth_data(df, SMOOTHING_FACTOR)
    plot_wiggle_streamgraph(x_smooth, y_smooth_dict, cats)
