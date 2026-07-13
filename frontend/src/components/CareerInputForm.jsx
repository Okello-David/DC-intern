import { useState } from 'react';
import { createCareerInput } from '../services/api';

const INPUT_TYPE_CHOICES = ['Resume Text', 'Career Goal', 'Internship Goal'];

const EMPTY_INPUT = {
  input_type: '',
  content: '',
};

function CareerInputForm({ studentProfileId, careerInputs, onCareerInputCreated }) {
  const [careerInput, setCareerInput] = useState(EMPTY_INPUT);
  const [status, setStatus] = useState('idle'); // idle | saving | success | error
  const [errorMessage, setErrorMessage] = useState('');

  const handleChange = (event) => {
    const { name, value } = event.target;
    setCareerInput({ ...careerInput, [name]: value });
  };

  const isValid = careerInput.input_type !== '' && careerInput.content.trim() !== '';

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!studentProfileId) {
      setStatus('error');
      setErrorMessage('Please save your student profile first.');
      return;
    }

    if (!isValid) {
      setStatus('error');
      setErrorMessage('Please select an input type and enter some content.');
      return;
    }

    setStatus('saving');
    setErrorMessage('');

    try {
      const createdInput = await createCareerInput({
        ...careerInput,
        student_profile: studentProfileId,
      });
      setStatus('success');
      setCareerInput(EMPTY_INPUT);
      onCareerInputCreated(createdInput);
    } catch (error) {
      setStatus('error');
      setErrorMessage(`Could not save entry: ${error.message}`);
    }
  };

  return (
    <section className="card">
      <h2>3. Resume or Career Goal</h2>

      {!studentProfileId && (
        <p className="message message-info">
          Save your student profile above before adding resume or career goal text.
        </p>
      )}

      <form className="form" onSubmit={handleSubmit}>
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

        <button type="submit" className="btn" disabled={status === 'saving'}>
          {status === 'saving' ? 'Saving career input...' : 'Add Entry'}
        </button>

        {status === 'success' && <p className="message message-success">Entry saved successfully.</p>}
        {status === 'error' && <p className="message message-error">{errorMessage}</p>}
      </form>

      {careerInputs.length > 0 && (
        <ul className="entry-list">
          {careerInputs.map((entry) => (
            <li key={entry.id}>
              <span>
                <strong>{entry.input_type}</strong>: {entry.content.slice(0, 60)}
                {entry.content.length > 60 ? '…' : ''}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default CareerInputForm;
