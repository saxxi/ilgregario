import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
SECRET_KEY = os.environ["SECRET_KEY"]

GC_SCORING = {
    "by_name": {
        "Tour de France":  [25, 20, 16, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        "Giro d'Italia":   [25, 20, 16, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        "Vuelta a España": [22, 18, 14, 11, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        "Paris-Roubaix":  [10, 7, 5, 3, 2, 1],
        "Milano-Sanremo": [10, 7, 5, 3, 2, 1],
        "Il Lombardia":   [10, 7, 5, 3, 2, 1],
    },
    "by_stages": [
        (1,   [6, 4, 2, 1]),
        (4,   [8, 5, 3, 1]),
        (8,   [12, 8, 5, 2, 1]),
        (14,  [16, 11, 7, 4, 2, 1]),
        (999, [22, 16, 12, 8, 5, 3, 1]),
    ],
    "default": [3, 1],
}

STAGE_SCORING = {
    "by_name": {
        "Tour de France":  [8, 5, 3, 2, 1],
        "Giro d'Italia":   [8, 5, 3, 2, 1],
        "Vuelta a España": [7, 4, 2, 1],
    },
    "by_stages": [
        (1,   [0]),
        (4,   [4, 2, 1]),
        (8,   [5, 3, 2, 1]),
        (999, [7, 4, 2, 1]),
    ],
    "default": [2, 1],
}
