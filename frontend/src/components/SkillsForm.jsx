import { useState } from 'react';
import { createSkill } from '../services/api';

const CATEGORY_CHOICES = [
  'Programming',
  'Web Development',
  'Database',
  'Cloud Computing',
  'Cybersecurity',
  'AI and Data',
  'Networking',
  'Software Engineering',
  'Professional Skills',
  'Other',
];

const CONFIDENCE_LEVEL_CHOICES = ['Beginner', 'Intermediate', 'Advanced'];

const EMPTY_SKILL = {
  name: '',
  category: '',
  confidence_level: '',
  evidence: '',
};

function SkillsForm({ studentProfileId, skills, onSkillCreated }) {
  const [skill, setSkill] = useState(EMPTY_SKILL);
  const [status, setStatus] = useState('idle'); // idle | saving | success | error
  const [errorMessage, setErrorMessage] = useState('');

  const handleChange = (event) => {
    const { name, value } = event.target;
    setSkill({ ...skill, [name]: value });
  };

  const isValid = skill.name.trim() !== '' && skill.category !== '' && skill.confidence_level !== '';

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!studentProfileId) {
      setStatus('error');
      setErrorMessage('Please save your student profile first.');
      return;
    }

    if (!isValid) {
      setStatus('error');
      setErrorMessage('Please enter a skill name, category, and confidence level.');
      return;
    }

    setStatus('saving');
    setErrorMessage('');

    try {
      const createdSkill = await createSkill({ ...skill, student_profile: studentProfileId });
      setStatus('success');
      setSkill(EMPTY_SKILL);
      onSkillCreated(createdSkill);
    } catch (error) {
      setStatus('error');
      setErrorMessage(`Could not save skill: ${error.message}`);
    }
  };

  return (
    <section className="card">
      <h2>2. Skills</h2>

      {!studentProfileId && (
        <p className="message message-info">Save your student profile above before adding skills.</p>
      )}

      <form className="form" onSubmit={handleSubmit}>
        <label htmlFor="skill_name">Skill Name</label>
        <input
          id="skill_name"
          name="name"
          type="text"
          value={skill.name}
          onChange={handleChange}
          placeholder="e.g. Python"
        />

        <label htmlFor="skill_category">Category</label>
        <select id="skill_category" name="category" value={skill.category} onChange={handleChange}>
          <option value="">Select category</option>
          {CATEGORY_CHOICES.map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>

        <label htmlFor="confidence_level">Confidence Level</label>
        <select
          id="confidence_level"
          name="confidence_level"
          value={skill.confidence_level}
          onChange={handleChange}
        >
          <option value="">Select confidence level</option>
          {CONFIDENCE_LEVEL_CHOICES.map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>

        <label htmlFor="evidence">Evidence (optional)</label>
        <textarea
          id="evidence"
          name="evidence"
          rows={2}
          value={skill.evidence}
          onChange={handleChange}
          placeholder="e.g. Built a Django REST API for a class project"
        />

        <button type="submit" className="btn" disabled={status === 'saving'}>
          {status === 'saving' ? 'Saving skill...' : 'Add Skill'}
        </button>

        {status === 'success' && <p className="message message-success">Skill saved successfully.</p>}
        {status === 'error' && <p className="message message-error">{errorMessage}</p>}
      </form>

      {skills.length > 0 && (
        <ul className="entry-list">
          {skills.map((entry) => (
            <li key={entry.id}>
              <span>
                <strong>{entry.name}</strong> — {entry.category} ({entry.confidence_level})
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default SkillsForm;
