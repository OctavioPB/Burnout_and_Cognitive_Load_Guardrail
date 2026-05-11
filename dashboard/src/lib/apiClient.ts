/**
 * Axios client with request interceptor that attaches auth identity headers.
 *
 * The interceptor reads from the Zustand store using getState() (not a hook)
 * so it works outside React component scope.
 */

import axios from 'axios';
import { useAuthStore } from '../stores/authStore';

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export const apiClient = axios.create({ baseURL: BASE });

apiClient.interceptors.request.use(config => {
  const user = useAuthStore.getState().user;
  if (user) {
    config.headers['X-User-Id']   = user.id;
    config.headers['X-User-Name'] = user.name;
    config.headers['X-User-Role'] = user.role;
    if (user.team_id) {
      config.headers['X-User-Team-Id'] = user.team_id;
    }
  }
  return config;
});
