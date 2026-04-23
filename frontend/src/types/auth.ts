export interface User {
  user_id: number;
  username: string;
  email: string;
  role: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  role: string;
}

export interface UserLogin {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}