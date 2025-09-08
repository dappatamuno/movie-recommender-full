import React, { useState, useEffect } from 'react';
import { API_BASE } from './config';
import logo from '../public/logo.png';

function App(){
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const userId = "jane";

  const fetchRecs = async () => {
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch(`${API_BASE}/recommend?user_id=${userId}&n=8`);
      const data = await res.json();

      // fetch posters for each recommended movie
      const moviesWithPosters = await Promise.all(
        (data.recommendations || []).map(async (m) => {
          try {
            const omdbRes = await fetch(`https://www.omdbapi.com/?t=${encodeURIComponent(m.title)}&apikey=b0530989`);
            const omdbData = await omdbRes.json();
            return {
              ...m,
              poster: (omdbData.Poster && omdbData.Poster !== "N/A") 
                ? omdbData.Poster 
                : "https://via.placeholder.com/300x450?text=No+Image"
            };
          } catch {
            return {
              ...m,
              poster: "https://via.placeholder.com/300x450?text=No+Image"
            };
          }
        })
      );

      setMovies(moviesWithPosters);
      setMessage('Here are today\'s picks for you — curated just now.');
    } catch (e) {
      setMessage('Failed to load recommendations.');
    } finally {
      setLoading(false);
    }
  };

  const sendFeedback = async (movie, value) => {
    try {
      await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({user: userId, movieId: movie.movieId, title: movie.title, feedback: value})
      });
      setMessage(value === 'like' ? 'Thanks — noted your like!' : 'Thanks — noted your dislike.');
    } catch (e) {
      setMessage('Failed to send feedback.');
    }
  };

  return (
    <div className="container">
      <header className="header">
        <img src={logo} alt="logo" className="logo" />
        <div className="header-text">
          <h1>Welcome back, Jane 👋</h1>
          <p className="caption">
            Personalized movie recommendations — fresh every day. 
            Curated with lightweight ML and delivered instantly.
          </p>
        </div>
      </header>

      <main>
        <div className="controls">
          <button onClick={fetchRecs} className="primary-btn">
            Movie Recommendations for Today
          </button>
          {loading && <span className="loading">Loading…</span>}
        </div>

        {message && <div className="message">{message}</div>}

        <section className="grid">
          {movies.map(m => (
            <article key={m.movieId} className="card">
              <div className="card-body">
                <img 
                  src={m.poster} 
                  alt={m.title} 
                  className="poster" 
                  style={{
                    width: "100%", 
                    height: "300px", 
                    objectFit: "cover", 
                    borderRadius: "10px", 
                    marginBottom: "10px"
                  }} 
                />
                <h3 className="title">{m.title}</h3>
                <p className="genres">{m.genres}</p>
                <div className="actions">
                  <button className="like" onClick={()=>sendFeedback(m,'like')}>👍</button>
                  <button className="dislike" onClick={()=>sendFeedback(m,'dislike')}>👎</button>
                  <a className="watch" href={m.watch_url} target="_blank" rel="noreferrer">Watch on Netflix</a>
                </div>
              </div>
            </article>
          ))}
        </section>

        <footer className="footer">
          <p>Built with free tools — Google Colab, GitHub, Render/Vercel. No paid services required.</p>
        </footer>
      </main>
    </div>
  );
}

export default App;
