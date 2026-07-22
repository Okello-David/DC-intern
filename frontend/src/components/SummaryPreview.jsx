function SummaryPreview({ profile, skills, careerInputs }) {
  return (
    <section className="card">
      <h2>4. Summary Preview</h2>
      <p className="hint">
        This reflects data already saved to the backend during this session.
      </p>

      <h3>Student Profile</h3>
      {profile ? (
        <dl className="summary-list">
          <dt>Full Name</dt>
          <dd>{profile.full_name}</dd>
          <dt>Field of Study</dt>
          <dd>{profile.field_of_study}</dd>
          <dt>Year of Study</dt>
          <dd>{profile.year_of_study}</dd>
          <dt>Career Interest</dt>
          <dd>{profile.career_interest}</dd>
          <dt>Internship Goal</dt>
          <dd>{profile.internship_goal}</dd>
        </dl>
      ) : (
        <p className="empty">No profile saved yet.</p>
      )}

      <h3>Skills ({skills.length})</h3>
      {skills.length > 0 ? (
        <ul className="summary-list-simple">
          {skills.map((skill) => (
            <li key={skill.id}>
              <strong>{skill.name}</strong> — {skill.category}, {skill.confidence_level}
              {skill.evidence ? ` (${skill.evidence})` : ''}
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty">No skills saved yet.</p>
      )}

      <h3>Resume / Career Inputs ({careerInputs.length})</h3>
      {careerInputs.length > 0 ? (
        <ul className="summary-list-simple">
          {careerInputs.map((entry) => (
            <li key={entry.id}>
              <strong>{entry.input_type}</strong>: {entry.content}
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty">No resume or career goal entries saved yet.</p>
      )}

      <p className="hint hint-note">
        Use the AI Recommendation panel below to generate a skill gap analysis from this
        data. Career path suggestions, project ideas, and learning plans follow later in
        Week 4.
      </p>
    </section>
  );
}

export default SummaryPreview;
