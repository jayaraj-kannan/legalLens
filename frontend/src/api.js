const API_BASE = import.meta.env.VITE_API_BASE || (typeof window !== 'undefined' && window.location.port === '5173' ? 'http://127.0.0.1:8080/api/v1' : '/api/v1');

export async function uploadDocument(file, userId = 'test_user_01', description = '', sessionId = '') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_id', userId);
  if (description) formData.append('description', description);
  if (sessionId) formData.append('session_id', sessionId);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function listDocuments(userId = 'test_user_01') {
  const res = await fetch(`${API_BASE}/documents?user_id=${encodeURIComponent(userId)}`);
  if (!res.ok) throw new Error('Failed to load documents');
  return res.json();
}

export async function createSession(userId, title, documentIds = []) {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      title: title || 'New Legal Review',
      document_ids: documentIds,
    }),
  });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
}

export async function listSessions(userId = 'test_user_01') {
  const res = await fetch(`${API_BASE}/sessions?user_id=${encodeURIComponent(userId)}`);
  if (!res.ok) throw new Error('Failed to fetch sessions');
  return res.json();
}

export async function deleteSession(sessionId, userId = 'test_user_01') {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete session');
  return res.json();
}

export async function renameSession(sessionId, newTitle) {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: newTitle }),
  });
  if (!res.ok) throw new Error('Failed to rename session');
  return res.json();
}

export async function getSessionDetails(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error('Failed to load session details');
  return res.json();
}

export async function getSessionEvents(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}/events`);
  if (!res.ok) throw new Error('Failed to load session audit events');
  return res.json();
}

export async function queryAgent(sessionId, userId, prompt, documentIds = []) {
  const res = await fetch(`${API_BASE}/agent/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      user_id: userId,
      prompt,
      document_ids: documentIds,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Query failed' }));
    throw new Error(err.detail || 'Query failed');
  }
  return res.json();
}

export async function getSessionDashboard(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}/dashboard`);
  if (!res.ok) throw new Error('Failed to load consultation dashboard');
  return res.json();
}

export async function analyzeSession(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}/analyze`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to run session analysis');
  return res.json();
}

export async function getDocumentAnalysis(documentId) {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(documentId)}/analysis`);
  if (!res.ok) throw new Error('Failed to load document breakdown');
  return res.json();
}

export async function analyzeDocument(documentId) {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(documentId)}/analyze`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to analyze document');
  return res.json();
}

export async function saveSessionDashboard(sessionId, dashboardData) {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}/dashboard`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dashboardData),
  });
  if (!res.ok) throw new Error('Failed to save consultation dashboard');
  return res.json();
}


