// Base URL for the Django REST Framework backend.
//
// Set at BUILD time by Vite from VITE_API_BASE_URL (see frontend/.env.example):
//
//   local development   VITE_API_BASE_URL unset -> http://127.0.0.1:8000/api
//                       (Vite dev server on :5173, Django on :8000, CORS allows it)
//   production          VITE_API_BASE_URL=/api
//                       Nginx serves the built React app and proxies /api/ to
//                       Gunicorn, so the browser calls its own origin.
//
// The relative "/api" is what makes the deployment portable: no public IP,
// hostname, or region is compiled into the bundle, so the same build works
// behind an IP today and a domain name with TLS tomorrow. It also removes
// cross-origin requests entirely — same origin means no CORS preflight and no
// origin list to keep in step with the server.
//
// Never put a secret in a VITE_* variable: everything Vite inlines is shipped
// to the browser and readable in the built JavaScript.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

// Messages shown to users are written here, deliberately. The backend's own
// `error`/`detail` text is safe to show (the views produce it), but anything
// else — a proxy's HTML error page, a network failure, a parse error — is
// summarised instead of being dumped on screen.
const GENERIC_ERROR = 'Something went wrong while contacting the server. Please try again.';
const OFFLINE_ERROR =
  'Could not reach the server. Check your connection and try again.';

function messageForStatus(status) {
  if (status === 404) return 'That record could not be found on the server.';
  if (status === 429) return 'Too many requests. Please wait a moment and try again.';
  if (status === 503) return 'The service is temporarily unavailable. Please try again shortly.';
  if (status >= 500) return 'The server had a problem completing that request. Please try again.';
  return GENERIC_ERROR;
}

async function readError(response) {
  // A JSON body from our own API carries a readable message; anything else
  // (an Nginx 502 page, an empty body) must not be shown verbatim.
  let body = null;
  try {
    body = await response.json();
  } catch {
    return messageForStatus(response.status);
  }

  if (typeof body?.error === 'string') return body.error;
  if (typeof body?.detail === 'string') return body.detail;

  // DRF field validation: {"full_name": ["This field is required."]}
  if (body && typeof body === 'object') {
    const fieldErrors = Object.entries(body)
      .filter(([, value]) => Array.isArray(value) && typeof value[0] === 'string')
      .map(([field, value]) => `${field}: ${value.join(' ')}`);
    if (fieldErrors.length > 0) return fieldErrors.join('\n');
  }

  return messageForStatus(response.status);
}

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch {
    // fetch only rejects for network-level failures (server down, DNS, CORS).
    // The underlying error text is not useful to a student, so it is replaced.
    throw new Error(OFFLINE_ERROR);
  }

  if (!response.ok) {
    throw new Error(await readError(response));
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
// The AI provider is called by the backend only: on AWS, Django calls Amazon
// Bedrock using the EC2 instance's IAM role. The browser never holds an AI
// credential, never sees a prompt, and does not know which provider is in use.
export function generateSkillGapAnalysis(profileId) {
  return request(`/profiles/${profileId}/generate-skill-gap/`, {
    method: 'POST',
  });
}
