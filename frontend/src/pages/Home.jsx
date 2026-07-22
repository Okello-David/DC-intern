import { useEffect, useState } from 'react';
import ProfileForm from '../components/ProfileForm';
import SkillsForm from '../components/SkillsForm';
import CareerInputForm from '../components/CareerInputForm';
import SummaryPreview from '../components/SummaryPreview';
import AIRecommendationPanel from '../components/AIRecommendationPanel';
import { getStudentProfiles } from '../services/api';

function Home() {
  const [currentProfile, setCurrentProfile] = useState(null);
  const [skills, setSkills] = useState([]);
  const [careerInputs, setCareerInputs] = useState([]);
  const [profilesLoading, setProfilesLoading] = useState(true);
  const [profilesError, setProfilesError] = useState('');

  useEffect(() => {
    getStudentProfiles()
      .then((profiles) => {
        if (profiles.length > 0) {
          setCurrentProfile(profiles[profiles.length - 1]);
        }
      })
      .catch((error) => {
        setProfilesError(`Could not load existing profiles: ${error.message}`);
      })
      .finally(() => setProfilesLoading(false));
  }, []);

  const handleProfileCreated = (profile) => {
    setCurrentProfile(profile);
  };

  const handleSkillCreated = (skill) => setSkills([...skills, skill]);
  const handleCareerInputCreated = (entry) => setCareerInputs([...careerInputs, entry]);

  return (
    <main className="page">
      <header className="intro">
        <h1>AI-Powered Student Career and Internship Assistant</h1>
        <p>
          A tool that helps university students in IT-related fields prepare for
          internships and early-career opportunities by turning their profile, skills,
          and goals into personalized recommendations.
        </p>

        <div className="status-badge">Week 4 — Local Build with AI-Assisted Skill Gap Analysis</div>

        <div className="workflow">
          <h2>MVP Workflow Status</h2>
          <ol className="workflow-status">
            <li className={currentProfile ? 'done' : ''}>
              {currentProfile ? '✓' : '○'} Profile created
            </li>
            <li className={skills.length > 0 ? 'done' : ''}>
              {skills.length > 0 ? '✓' : '○'} Skills added ({skills.length})
            </li>
            <li className={careerInputs.length > 0 ? 'done' : ''}>
              {careerInputs.length > 0 ? '✓' : '○'} Resume/career input submitted (
              {careerInputs.length})
            </li>
          </ol>
          <p className="hint">
            Form submissions below are saved to the Django backend API in real time.
          </p>
          {profilesLoading && <p className="hint">Loading existing profiles...</p>}
          {profilesError && <p className="message message-error">{profilesError}</p>}
        </div>
      </header>

      <ProfileForm onProfileCreated={handleProfileCreated} />
      <SkillsForm
        studentProfileId={currentProfile?.id}
        skills={skills}
        onSkillCreated={handleSkillCreated}
      />
      <CareerInputForm
        studentProfileId={currentProfile?.id}
        careerInputs={careerInputs}
        onCareerInputCreated={handleCareerInputCreated}
      />
      <SummaryPreview profile={currentProfile} skills={skills} careerInputs={careerInputs} />
      <AIRecommendationPanel profile={currentProfile} />
    </main>
  );
}

export default Home;
