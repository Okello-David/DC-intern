// Base URL for the Django REST Framework backend.
export const API_BASE_URL = 'http://127.0.0.1:8000/api';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    // The backend sends readable messages in `error` (our own views) or
    // `detail` (DRF defaults, e.g. 404); fall back to the raw body otherwise.
    const message =
      body?.error || body?.detail || (body ? JSON.stringify(body) : null) ||
      `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function getStudentProfiles() {
  return request('/profiles/');
}

export function createStudentProfile(profileData) {
  return request('/profiles/', {
    method: 'POST',
    body: JSON.stringify(profileData),
  });
}

export function getSkills() {
  return request('/skills/');
}

export function createSkill(skillData) {
  return request('/skills/', {
    method: 'POST',
    body: JSON.stringify(skillData),
  });
}

export function getCareerInputs() {
  return request('/career-inputs/');
}

export function createCareerInput(careerInputData) {
  return request('/career-inputs/', {
    method: 'POST',
    body: JSON.stringify(careerInputData),
  });
}

export function getRecommendations() {
  return request('/recommendations/');
}

// Asks the Django backend to generate a skill gap analysis for one profile.
// The AI provider is called by the backend only — the browser never sees the
// AI API key, and this app never talks to an AI provider directly.
export function generateSkillGapAnalysis(profileId) {
  return request(`/profiles/${profileId}/generate-skill-gap/`, {
    method: 'POST',
  });
}
