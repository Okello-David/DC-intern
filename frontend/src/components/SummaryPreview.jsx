function SummaryPreview({ profile, skills, careerInputs }) {
  const hasProfile = Object.values(profile).some((value) => value.trim() !== '');

  return (
    <section className="card">
      <h2>4. Summary Preview</h2>
      <p className="hint">
        This is a live preview of what you've entered above. Nothing is saved yet — that
        happens once the frontend is connected to the backend on Day 4.
      </p>

      <h3>Student Profile</h3>
      {hasProfile ? (
        <dl className="summary-list">
          <dt>Full Name</dt>
          <dd>{profile.full_name || '—'}</dd>
          <dt>Field of Study</dt>
          <dd>{profile.field_of_study || '—'}</dd>
          <dt>Year of Study</dt>
          <dd>{profile.year_of_study || '—'}</dd>
          <dt>Career Interest</dt>
          <dd>{profile.career_interest || '—'}</dd>
          <dt>Internship Goal</dt>
          <dd>{profile.internship_goal || '—'}</dd>
        </dl>
      ) : (
        <p className="empty">No profile information entered yet.</p>
      )}

      <h3>Skills ({skills.length})</h3>
      {skills.length > 0 ? (
        <ul className="summary-list-simple">
          {skills.map((skill, index) => (
            <li key={index}>
              <strong>{skill.name}</strong> — {skill.category}, {skill.confidence_level}
              {skill.evidence ? ` (${skill.evidence})` : ''}
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty">No skills added yet.</p>
      )}

      <h3>Resume / Career Inputs ({careerInputs.length})</h3>
      {careerInputs.length > 0 ? (
        <ul className="summary-list-simple">
          {careerInputs.map((entry, index) => (
            <li key={index}>
              <strong>{entry.input_type}</strong>: {entry.content}
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty">No resume or career goal entries added yet.</p>
      )}
    </section>
  );
}

export default SummaryPreview;
