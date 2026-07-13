import { useState } from 'react';
import { createStudentProfile } from '../services/api';

const FIELD_OF_STUDY_CHOICES = [
  'Software Engineering',
  'Computer Science',
  'Information Technology',
  'Information Systems',
  'Cybersecurity',
  'Data Science',
  'Computer Engineering',
  'Other IT Related Field',
];

const YEAR_OF_STUDY_CHOICES = ['Year 1', 'Year 2', 'Year 3', 'Year 4', 'Final Year'];

const EMPTY_PROFILE = {
  full_name: '',
  field_of_study: '',
  year_of_study: '',
  career_interest: '',
  internship_goal: '',
};

function ProfileForm({ onProfileCreated }) {
  const [profile, setProfile] = useState(EMPTY_PROFILE);
  const [status, setStatus] = useState('idle'); // idle | saving | success | error
  const [errorMessage, setErrorMessage] = useState('');

  const handleChange = (event) => {
    const { name, value } = event.target;
    setProfile({ ...profile, [name]: value });
  };

  const isValid = Object.values(profile).every((value) => value.trim() !== '');

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!isValid) {
      setStatus('error');
      setErrorMessage('Please fill in all profile fields before saving.');
      return;
    }

    setStatus('saving');
    setErrorMessage('');

    try {
      const createdProfile = await createStudentProfile(profile);
      setStatus('success');
      setProfile(EMPTY_PROFILE);
      onProfileCreated(createdProfile);
    } catch (error) {
      setStatus('error');
      setErrorMessage(`Could not save profile: ${error.message}`);
    }
  };

  return (
    <section className="card">
      <h2>1. Student Profile</h2>
      <form className="form" onSubmit={handleSubmit}>
        <label htmlFor="full_name">Full Name</label>
        <input
          id="full_name"
          name="full_name"
          type="text"
          value={profile.full_name}
          onChange={handleChange}
          placeholder="e.g. Jane Doe"
        />

        <label htmlFor="field_of_study">Field of Study</label>
        <select
          id="field_of_study"
          name="field_of_study"
          value={profile.field_of_study}
          onChange={handleChange}
        >
          <option value="">Select field of study</option>
          {FIELD_OF_STUDY_CHOICES.map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>

        <label htmlFor="year_of_study">Year of Study</label>
        <select
          id="year_of_study"
          name="year_of_study"
          value={profile.year_of_study}
          onChange={handleChange}
        >
          <option value="">Select year of study</option>
          {YEAR_OF_STUDY_CHOICES.map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>

        <label htmlFor="career_interest">Career Interest</label>
        <input
          id="career_interest"
          name="career_interest"
          type="text"
          value={profile.career_interest}
          onChange={handleChange}
          placeholder="e.g. Backend Engineering"
        />

        <label htmlFor="internship_goal">Internship Goal</label>
        <textarea
          id="internship_goal"
          name="internship_goal"
          rows={3}
          value={profile.internship_goal}
          onChange={handleChange}
          placeholder="What do you hope to get out of an internship?"
        />

        <button type="submit" className="btn" disabled={status === 'saving'}>
          {status === 'saving' ? 'Saving profile...' : 'Save Profile'}
        </button>

        {status === 'success' && (
          <p className="message message-success">Profile saved successfully.</p>
        )}
        {status === 'error' && <p className="message message-error">{errorMessage}</p>}
      </form>
    </section>
  );
}

export default ProfileForm;
