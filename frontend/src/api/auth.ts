import { api } from './client';
import type { LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, User } from '../types/auth';

export const authApi = {
  login: (payload: LoginRequest) => api.post<LoginResponse>('/auth/login', payload),
  register: (payload: RegisterRequest) => api.post<RegisterResponse>('/auth/register', payload),
  me: () => api.get<User>('/auth/me'),
};
