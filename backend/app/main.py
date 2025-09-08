from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os, json, joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import random

app = FastAPI(title="Movie Recommender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "model.pkl")
MOVIES_PATH = os.path.join(BASE_DIR, "model", "movies.csv")
FEEDBACK_LOG = os.path.join(BASE_DIR, "model", "feedback_log.jsonl")

# Load movies metadata (must exist)
if os.path.exists(MOVIES_PATH):
    movies_df = pd.read_csv(MOVIES_PATH)
else:
    movies_df = pd.DataFrame([{'movieId':1,'title':'Toy Story (1995)','genres':'Animation|Children|Comedy'}])

# Try load a model (pickled). If not available, fallback to a simple content-similarity using TF-IDF on title+genres.
model = None
tfidf = None
cosine_sim = None
try:
    model = joblib.load(MODEL_PATH)
    print("Loaded model from", MODEL_PATH)
except Exception as e:
    print("No pickled model found or failed to load:", e)
    # build TF-IDF fallback
    movies_df['text'] = movies_df['title'].fillna('') + ' ' + movies_df['genres'].fillna('')
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(movies_df['text'])
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
    print("Built TF-IDF fallback recommender.")

def get_top_n_recommendations_for_user(user_id: str, n: int = 10):
    # If pickled model exists and has a predict method, attempt ranking by model (best-effort).
    if model is not None:
        # model could be a surprise model or sklearn pipeline. We attempt to predict by scoring all items.
        scores = []
        for _, row in movies_df.iterrows():
            mid = row.get('movieId')
            try:
                # Some models expect string ids
                pred = model.predict(str(user_id), str(mid))
                est = getattr(pred, 'est', None)
                if est is None:
                    est = float(pred)
                scores.append((mid, float(est)))
            except Exception:
                # fallback: random score
                scores.append((mid, random.random()))
        scores.sort(key=lambda x: x[1], reverse=True)
        top_ids = [s[0] for s in scores[:n]]
        return movies_df[movies_df['movieId'].isin(top_ids)].to_dict(orient='records')
    else:
        # fallback content-based: pick a random seed movie and return top similar
        try:
            # pick random seed index
            idx = random.randrange(0, len(movies_df))
            sim_scores = list(enumerate(cosine_sim[idx]))
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
            top_indices = [i for i, _ in sim_scores[1:n+1]]
            return movies_df.iloc[top_indices].to_dict(orient='records')
        except Exception:
            # final fallback: random sample
            return movies_df.sample(n=min(n, len(movies_df))).to_dict(orient='records')

@app.get("/health")
async def health():
    return {"status":"ok", "model_loaded": model is not None}

@app.get("/recommend")
async def recommend(user_id: str = "jane", n: int = 10):
    recs = get_top_n_recommendations_for_user(user_id, n)
    # decorate with watch link (Netflix search)
    for r in recs:
        title_query = r.get('title','').split(' (')[0]
        r['watch_url'] = f"https://www.netflix.com/search?q={title_query.replace(' ', '%20')}"
    return {"user_id": user_id, "recommendations": recs}

@app.post("/feedback")
async def feedback(req: Request):
    data = await req.json()
    # Append to jsonl for simple storage
    os.makedirs(os.path.dirname(FEEDBACK_LOG), exist_ok=True)
    with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")
    return {"status":"logged"}
