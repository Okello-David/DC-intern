import { useState } from 'react';
import { generateSkillGapAnalysis } from '../services/api';

function AIRecommendationPanel({ profile }) {
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!profile) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      // The browser only ever calls our own Django API. Django holds the AI
      // API key and makes the provider call server-side.
      const result = await generateSkillGapAnalysis(profile.id);
      setRecommendation(result);
    } catch (err) {
      setError(`Could not generate the analysis: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card">
      <h2>5. AI Recommendation</h2>
      <p className="hint">
        Generates a skill gap analysis from the profile, skills, and career inputs saved
        for this student.
      </p>

      {!profile && (
        <p className="message message-info">
          Save a student profile first — the analysis needs a profile to work from.
        </p>
      )}

      <button
        type="button"
        className="btn"
        onClick={handleGenerate}
        disabled={!profile || loading}
      >
        {loading ? 'Generating analysis...' : 'Generate Skill Gap Analysis'}
      </button>

      {loading && (
        <p className="hint">Asking the backend to generate your analysis. This can take a moment.</p>
      )}

      {error && <p className="message message-error">{error}</p>}

      {recommendation && !loading && (
        <div className="recommendation">
          <h3>{recommendation.recommendation_type}</h3>
          <p className="hint">
            Generated {new Date(recommendation.created_at).toLocaleString()}
            {recommendation.used_fallback ? ' · local mock response' : ` · ${recommendation.ai_model}`}
          </p>

          {recommendation.notes?.map((note) => (
            <p className="message message-info" key={note}>
              {note}
            </p>
          ))}

          <pre className="recommendation-content">{recommendation.content}</pre>
        </div>
      )}

      <p className="hint hint-note">
        This is the Week 4 AI-assisted feature. In local mode, it may use a mock AI
        response unless a real AI provider is configured.
      </p>
    </section>
  );
}

export default AIRecommendationPanel;
