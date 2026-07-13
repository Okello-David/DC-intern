import { useState } from 'react';

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

function SkillsForm({ skills, onAdd, onRemove }) {
  const [skill, setSkill] = useState(EMPTY_SKILL);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setSkill({ ...skill, [name]: value });
  };

  const handleAdd = (event) => {
    event.preventDefault();
    if (!skill.name || !skill.category || !skill.confidence_level) {
      return;
    }
    onAdd(skill);
    setSkill(EMPTY_SKILL);
  };

  return (
    <section className="card">
      <h2>2. Skills</h2>
      <form className="form">
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

        <button type="button" className="btn" onClick={handleAdd}>
          Add Skill
        </button>
      </form>

      {skills.length > 0 && (
        <ul className="entry-list">
          {skills.map((entry, index) => (
            <li key={index}>
              <span>
                <strong>{entry.name}</strong> — {entry.category} ({entry.confidence_level})
              </span>
              <button type="button" className="btn-link" onClick={() => onRemove(index)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default SkillsForm;
