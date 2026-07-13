import { useState } from 'react';
import ProfileForm from '../components/ProfileForm';
import SkillsForm from '../components/SkillsForm';
import CareerInputForm from '../components/CareerInputForm';
import SummaryPreview from '../components/SummaryPreview';

const EMPTY_PROFILE = {
  full_name: '',
  field_of_study: '',
  year_of_study: '',
  career_interest: '',
  internship_goal: '',
};

function Home() {
  const [profile, setProfile] = useState(EMPTY_PROFILE);
  const [skills, setSkills] = useState([]);
  const [careerInputs, setCareerInputs] = useState([]);

  const addSkill = (skill) => setSkills([...skills, skill]);
  const removeSkill = (index) => setSkills(skills.filter((_, i) => i !== index));

  const addCareerInput = (entry) => setCareerInputs([...careerInputs, entry]);
  const removeCareerInput = (index) =>
    setCareerInputs(careerInputs.filter((_, i) => i !== index));

  return (
    <main className="page">
      <header className="intro">
        <h1>AI-Powered Student Career and Internship Assistant</h1>
        <p>
          A tool that helps university students in IT-related fields prepare for
          internships and early-career opportunities by turning their profile, skills,
          and goals into personalized recommendations.
        </p>

        <div className="status-badge">Week 3 MVP — Frontend Setup (Day 3)</div>

        <div className="workflow">
          <h2>How it works</h2>
          <ol>
            <li>Create your student profile</li>
            <li>Add your skills</li>
            <li>Add your resume text or career goal</li>
            <li>View a summary preview</li>
          </ol>
          <p className="hint">
            On Day 3, this page builds and previews your data locally. Saving to the
            backend API is coming on Day 4.
          </p>
        </div>
      </header>

      <ProfileForm profile={profile} onChange={setProfile} />
      <SkillsForm skills={skills} onAdd={addSkill} onRemove={removeSkill} />
      <CareerInputForm
        careerInputs={careerInputs}
        onAdd={addCareerInput}
        onRemove={removeCareerInput}
      />
      <SummaryPreview profile={profile} skills={skills} careerInputs={careerInputs} />
    </main>
  );
}

export default Home;
