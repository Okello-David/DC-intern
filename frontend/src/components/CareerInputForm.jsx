import { useState } from 'react';

const INPUT_TYPE_CHOICES = ['Resume Text', 'Career Goal', 'Internship Goal'];

const EMPTY_INPUT = {
  input_type: '',
  content: '',
};

function CareerInputForm({ careerInputs, onAdd, onRemove }) {
  const [careerInput, setCareerInput] = useState(EMPTY_INPUT);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setCareerInput({ ...careerInput, [name]: value });
  };

  const handleAdd = (event) => {
    event.preventDefault();
    if (!careerInput.input_type || !careerInput.content) {
      return;
    }
    onAdd(careerInput);
    setCareerInput(EMPTY_INPUT);
  };

  return (
    <section className="card">
      <h2>3. Resume or Career Goal</h2>
      <form className="form">
        <label htmlFor="input_type">Input Type</label>
        <select id="input_type" name="input_type" value={careerInput.input_type} onChange={handleChange}>
          <option value="">Select input type</option>
          {INPUT_TYPE_CHOICES.map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>

        <label htmlFor="content">Content</label>
        <textarea
          id="content"
          name="content"
          rows={4}
          value={careerInput.content}
          onChange={handleChange}
          placeholder="Paste resume text or describe your career/internship goal"
        />

        <button type="button" className="btn" onClick={handleAdd}>
          Add Entry
        </button>
      </form>

      {careerInputs.length > 0 && (
        <ul className="entry-list">
          {careerInputs.map((entry, index) => (
            <li key={index}>
              <span>
                <strong>{entry.input_type}</strong>: {entry.content.slice(0, 60)}
                {entry.content.length > 60 ? '…' : ''}
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

export default CareerInputForm;
