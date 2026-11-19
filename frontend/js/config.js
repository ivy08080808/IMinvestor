// Backend base URL. Change the port here if the backend runs elsewhere.
export const API_BASE = 'http://localhost:8000';

// Market status / account summary polling interval (ms). Keeps two open
// browser windows in sync without WebSockets (plan §5.3).
export const POLL_MS = 5000;
